import os
import sys

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Blueprint, request, jsonify
import urllib.request
import urllib.parse
import urllib.error
import json
import uuid
import re
import base64
import time
import tempfile
from datetime import datetime

import config
from utils import database as db
from utils import security as sec
from utils import ai_helper as ai
from routes.auth import check_user_trial_status

webhook_bp = Blueprint('webhook_n8n', __name__)

def count_today_posts_for_key(api_key):
    """Menghitung jumlah postingan sukses yang sudah dilakukan API Key hari ini."""
    today_str = datetime.now().strftime("%d/%m/%Y")
    sheet = db.get_logs_sheet()
    count = 0
    if sheet:
        try:
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                for row in all_values[1:]:
                    if len(row) >= 5:
                        row_date = str(row[0]).split()[0] if len(row) > 0 else ""
                        row_key = str(row[2]).strip() if len(row) > 2 else ""
                        row_status = str(row[4]).upper() if len(row) > 4 else ""
                        
                        if row_key == api_key and today_str in row_date and ("SUCCESS" in row_status or "PUBLISHED" in row_status):
                            count += 1
        except Exception as e:
            print(f"Error checking daily post count: {e}")
    return count

@webhook_bp.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json or {}
    pesan_user = data.get('pesan_user', '')
    balasan = ai.get_ai_chat_response(pesan_user)
    return jsonify({"balasan": balasan})

@webhook_bp.route('/api/create-transaction', methods=['POST'])
def create_transaction():
    data = request.json or {}
    name = data.get('name', 'User')
    email = data.get('email', 'user@example.com').strip().lower()
    price_str = data.get('price', '200000')
    is_upgrading = data.get('isUpgrading', False)

    existing_user = db.db_get_user(email)
    if existing_user and not is_upgrading:
        return jsonify({"success": False, "message": "Email sudah terdaftar!"})
    try:
        amount = int(re.sub(r'[^\d]', '', price_str))
    except Exception:
        amount = 200000

    order_id = f"ORDER-{uuid.uuid4().hex[:8].upper()}"
    auth_string = base64.b64encode(f"{config.MIDTRANS_SERVER_KEY}:".encode()).decode()
    payload = {
        "transaction_details": {"order_id": order_id, "gross_amount": amount},
        "customer_details": {"first_name": name, "email": email}
    }

    try:
        req = urllib.request.Request(
            config.MIDTRANS_API_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={"Authorization": f"Basic {auth_string}", "Content-Type": "application/json"}, 
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if response.status == 201:
                if not existing_user:
                    db.db_save_user(email, sec.generate_base32_secret(), False, name, "-", "Pending Payment")
                return jsonify({"success": True, "token": res_data.get('token')})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@webhook_bp.route('/api/check-payment', methods=['POST'])
def check_payment():
    return jsonify({"success": True, "isPaid": False})

@webhook_bp.route('/api/n8n-webhook', methods=['GET', 'POST'], strict_slashes=False)
def n8n_webhook():
    if request.method == 'GET':
        return jsonify({"success": False, "message": "🟢 Endpoint Aktif! Harap gunakan method POST dari n8n."}), 200

    api_key = request.headers.get('X-API-Key', '').strip()
    if not api_key:
        auth_header = request.headers.get('Authorization', '').strip()
        if auth_header.startswith('Bearer '):
            api_key = auth_header.replace('Bearer ', '')

    if not api_key:
        return jsonify({"success": False, "message": "API Key is required in Header"}), 400

    # 1. VERIFIKASI USER BERDASARKAN API KEY DI SHEET UTAMA
    user_data = None
    sheet_users = db.get_gsheet()
    if sheet_users:
        try:
            all_vals = sheet_users.get_all_values()
            for r in all_vals[1:]:
                if len(r) >= 5 and str(r[4]).strip() == api_key:
                    user_data = db.db_get_user(r[0])
                    break
        except Exception as e:
            print(f"Error finding user by API key: {e}")

    # 2. VERIFIKASI TRIAL & KUOTA POSTING
    if user_data:
        trial_info = check_user_trial_status(user_data)
        
        # Jika Trial EXPIRED (> 7 hari) -> Blokir posting
        if trial_info["is_expired"] and not trial_info["is_paid"]:
            return jsonify({
                "success": False,
                "status": "FAILED",
                "message": "Masa Free Trial 1 Minggu Anda telah habis! Silakan upgrade akun ke berbayar di Dashboard TRENDORA.",
                "details": {"error": "Free Trial Expired (> 7 hari). Silakan upgrade ke akun berbayar."}
            }), 400
            
        # Jika Trial masih aktif (<= 7 hari) -> Cek batas 1 video per hari
        if trial_info["is_trial"] and not trial_info["is_paid"]:
            today_posts = count_today_posts_for_key(api_key)
            if today_posts >= 1:
                return jsonify({
                    "success": False,
                    "status": "FAILED",
                    "message": "Batas Free Trial tercapai! Akun Free Trial hanya diperbolehkan posting maksimal 1 video per hari. Silakan upgrade ke akun berbayar.",
                    "details": {"error": "Maksimal 1 video per hari untuk akun Free Trial."}
                }), 400

    data = request.json or {}
    platform = data.get('platform', 'unknown').lower()
    status = data.get('status', 'RECEIVED')
    details = data.get('details', {})
    
    if platform == 'tiktok' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Diposting otomatis via n8n & TRENDORA! 🚀')
        if media_url:
            user_tokens = db.db_get_tiktok_tokens_by_api_key(api_key)
            access_token = user_tokens.get('access_token')
            if access_token:
                temp_file_path = None
                try:
                    temp_dir = tempfile.gettempdir()
                    temp_file_path = os.path.join(temp_dir, f"tk_{uuid.uuid4().hex[:6]}.mp4")
                    
                    try:
                        req_download = urllib.request.Request(
                            media_url, 
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                        )
                        with urllib.request.urlopen(req_download) as res_dl, open(temp_file_path, 'wb') as out_file:
                            out_file.write(res_dl.read())
                    except urllib.error.HTTPError as dl_err:
                        status = "FAILED"
                        details['tiktok_error'] = f"[Google Storage Download Error] URL video tidak bisa diunduh/private. HTTP {dl_err.code}: {dl_err.reason}."
                        raise Exception(f"Media URL Download Failed: {dl_err}")

                    file_size = os.path.getsize(temp_file_path)

                    headers = {
                        "Authorization": f"Bearer {access_token}", 
                        "Content-Type": "application/json; charset=utf-8"
                    }

                    # Mode Production (Audited / Approved): Default Publik (PUBLIC_TO_EVERYONE)
                    # Bisa juga di-override via n8n payload: "privacy_level": "SELF_ONLY" / "PUBLIC_TO_EVERYONE"
                    privacy_level = details.get('privacy_level', 'PUBLIC_TO_EVERYONE')

                    payload = {
                        "post_info": {
                            "title": caption, 
                            "privacy_level": privacy_level, 
                            "disable_duet": False, 
                            "disable_comment": False, 
                            "disable_stitch": False
                        },
                        "source_info": {
                            "source": "FILE_UPLOAD", 
                            "video_size": file_size, 
                            "chunk_size": file_size, 
                            "total_chunk_count": 1
                        }
                    }
                    req_init = urllib.request.Request(
                        "https://open.tiktokapis.com/v2/post/publish/video/init/", 
                        data=json.dumps(payload).encode('utf-8'), 
                        headers=headers, 
                        method='POST'
                    )
                    
                    with urllib.request.urlopen(req_init) as response:
                        tiktok_res = json.loads(response.read().decode('utf-8'))
                        upload_url = tiktok_res.get('data', {}).get('upload_url')
                        if upload_url:
                            with open(temp_file_path, 'rb') as f:
                                video_data = f.read()
                            put_headers = {
                                'Content-Type': 'video/mp4', 
                                'Content-Range': f'bytes 0-{file_size-1}/{file_size}'
                            }
                            req_put = urllib.request.Request(upload_url, data=video_data, headers=put_headers, method='PUT')
                            urllib.request.urlopen(req_put)
                            status = "PUBLISHED (SUCCESS)"
                            details['upload_status'] = f"Success TikTok Upload ({file_size} bytes) - Mode: {privacy_level}."
                        else:
                            status = "FAILED"
                            details['tiktok_error'] = tiktok_res.get('error', {}).get('message', 'Gagal mendapatkan Upload URL dari TikTok')

                except urllib.error.HTTPError as http_err:
                    if 'tiktok_error' not in details:
                        status = "FAILED"
                        err_body = ""
                        try:
                            err_body = http_err.read().decode('utf-8')
                        except Exception:
                            pass
                        details['tiktok_error'] = f"[TikTok API 403/Forbidden] HTTP {http_err.code}: {http_err.reason}. Details: {err_body[:200]}"
                except Exception as e:
                    if 'tiktok_error' not in details:
                        details['tiktok_error'] = str(e)
                        status = "FAILED"
                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                        except Exception:
                            pass
            else:
                details['tiktok_error'] = "Akun TikTok belum terhubung atau Access Token kosong."
                status = "FAILED"

    elif platform == 'facebook' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Auto-post by TRENDORA ⚡')
        meta_token = db.db_get_meta_token_by_api_key(api_key)
        if meta_token and media_url:
            try:
                page_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={meta_token}"
                with urllib.request.urlopen(urllib.request.Request(page_url)) as response:
                    page_data = json.loads(response.read().decode('utf-8'))
                if page_data.get('data') and len(page_data['data']) > 0:
                    page_id = page_data['data'][0]['id']
                    page_token = page_data['data'][0]['access_token']
                    fb_post_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
                    fb_payload = urllib.parse.urlencode({'file_url': media_url, 'description': caption, 'access_token': page_token}).encode('utf-8')
                    with urllib.request.urlopen(urllib.request.Request(fb_post_url, data=fb_payload, method='POST')) as res_post:
                        fb_res = json.loads(res_post.read().decode('utf-8'))
                        status = "PUBLISHED (SUCCESS)"
                        details['fb_status'] = "Video sukses dipost ke Facebook Page"
                        details['fb_video_id'] = fb_res.get('id')
                else:
                    status = "FAILED"
                    details['meta_error'] = "Tidak menemukan Facebook Page."
            except Exception as e:
                status = "FAILED"
                details['meta_error'] = str(e)

    elif platform == 'instagram' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Auto-post Reels by TRENDORA ⚡')
        meta_token = db.db_get_meta_token_by_api_key(api_key)
        if meta_token and media_url:
            try:
                page_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={meta_token}"
                with urllib.request.urlopen(urllib.request.Request(page_url)) as response:
                    page_data = json.loads(response.read().decode('utf-8'))
                if page_data.get('data') and len(page_data['data']) > 0:
                    page_id = page_data['data'][0]['id']
                    ig_info_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={meta_token}"
                    with urllib.request.urlopen(urllib.request.Request(ig_info_url)) as res_ig:
                        ig_data = json.loads(res_ig.read().decode('utf-8'))
                    ig_user_id = ig_data.get('instagram_business_account', {}).get('id')
                    if ig_user_id:
                        ig_container_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
                        ig_payload = urllib.parse.urlencode({'media_type': 'REELS', 'video_url': media_url, 'caption': caption, 'access_token': meta_token}).encode('utf-8')
                        with urllib.request.urlopen(urllib.request.Request(ig_container_url, data=ig_payload, method='POST')) as res_cont:
                            cont_data = json.loads(res_cont.read().decode('utf-8'))
                            creation_id = cont_data.get('id')
                        time.sleep(5)
                        ig_publish_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
                        ig_pub_payload = urllib.parse.urlencode({'creation_id': creation_id, 'access_token': meta_token}).encode('utf-8')
                        try:
                            with urllib.request.urlopen(urllib.request.Request(ig_publish_url, data=ig_pub_payload, method='POST')) as res_pub:
                                pub_data = json.loads(res_pub.read().decode('utf-8'))
                                status = "PUBLISHED (SUCCESS)"
                                details['ig_status'] = "Sukses upload Instagram Reels!"
                                details['ig_media_id'] = pub_data.get('id')
                        except urllib.error.HTTPError:
                            status = "PENDING / RENDERING"
                            details['ig_status'] = f"Video diproses Instagram (ID: {creation_id})."
            except Exception as e:
                status = "FAILED"
                details['meta_error'] = str(e)

    media_url_val = details.pop('media_url', '') if isinstance(details, dict) else ''
    caption_val = details.pop('caption', '') if isinstance(details, dict) else ''
    hashtag_val = details.pop('hashtag', '') if isinstance(details, dict) else ''
    details_str = json.dumps(details) if isinstance(details, dict) else str(details)
        
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
    row_data = [timestamp, log_id, api_key, platform, status, details_str, "", media_url_val, caption_val, hashtag_val]
    
    # KETAT: Memastikan log hanya ditulis ke tab 'Logs' (bukan Sheet Utama)
    sheet_logs = db.get_logs_sheet()
    if sheet_logs:
        try:
            col_a = sheet_logs.col_values(1)
            next_row = len(col_a) + 1
            sheet_logs.update(values=[row_data], range_name=f"A{next_row}:J{next_row}")
        except Exception as e:
            print(f"Log sheet update error: {e}")
    else:
        if 'logs' not in config.user_2fa_store:
            config.user_2fa_store['logs'] = []
        config.user_2fa_store['logs'].append({
            "Timestamp": timestamp, "LogID": log_id, "APIKey": api_key, "Platform": platform, 
            "Status": status, "Details": details_str, "Keterangan": "", "MediaURL": media_url_val, 
            "Caption": caption_val, "Hashtag": hashtag_val
        })
        
    is_upload_success = "SUCCESS" in status or status == "PUBLISHED"
    return jsonify({
        "success": is_upload_success, 
        "status": status,
        "message": "Processed & Logged" if is_upload_success else "Upload Gagal / Tertunda", 
        "log_id": log_id,
        "details": details
    })

@webhook_bp.route('/api/get-logs', methods=['POST', 'GET'])
def get_logs():
    api_key = request.headers.get('X-API-Key', '').strip() or (request.json or {}).get('api_key', '').strip()
    logs = []
    sheet_logs = db.get_logs_sheet()
    
    if sheet_logs:
        try:
            all_values = sheet_logs.get_all_values()
            if len(all_values) > 1:
                for row in all_values[1:]:
                    if len(row) >= 3:
                        if api_key and str(row[2]).strip() != api_key:
                            continue
                        logs.append({
                            "Timestamp": str(row[0]).strip() if len(row) > 0 else "-", 
                            "LogID": str(row[1]).strip() if len(row) > 1 else "-",
                            "Platform": str(row[3]).strip() if len(row) > 3 else "-", 
                            "Status": str(row[4]).strip() if len(row) > 4 else "-",
                            "Details": str(row[5]).strip() if len(row) > 5 else "-"
                        })
            logs.reverse()
            return jsonify({"success": True, "logs": logs[:50]})
        except Exception as e: 
            return jsonify({"success": False, "message": str(e)})
    
    if 'logs' in config.user_2fa_store:
        all_mem = config.user_2fa_store['logs']
        logs = [log for log in all_mem if log.get('APIKey') == api_key] if api_key else all_mem
        logs.reverse()
        return jsonify({"success": True, "logs": logs[:50]})
        
    return jsonify({"success": True, "logs": []})