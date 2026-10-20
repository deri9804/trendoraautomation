import os
import sys

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Blueprint, request, jsonify, session, Response
import urllib.request
import urllib.parse
import uuid
import json
import base64
import hmac
import hashlib
from datetime import datetime

import config
from utils import database as db
from routes.auth import check_user_trial_status

oauth_bp = Blueprint('oauth_social', __name__)

def check_trial_social_limit(email=None):
    """
    Memeriksa apakah akun trial sudah melebihi batas 2 sosial media atau sudah expired.
    Return (can_connect: bool, error_message: str)
    """
    if not email:
        email = session.get('user_email', '').strip().lower()

    if not email:
        return False, "Sesi login tidak ditemukan atau email tidak valid. Silakan muat ulang halaman atau login kembali."
        
    user_data = db.db_get_user(email)
    if not user_data:
        return False, f"User dengan email '{email}' tidak ditemukan di database."
        
    trial_info = check_user_trial_status(user_data)
    
    # Jika user berbayar, bebas hubungkan berapa saja
    if trial_info["is_paid"]:
        return True, ""
        
    # Jika trial sudah expired
    if trial_info["is_expired"]:
        return False, "Masa Free Trial 1 Minggu Anda telah habis. Silakan upgrade ke akun berbayar untuk menautkan sosial media."
        
    # Hitung jumlah sosial media terhubung
    connected_count = 0
    if user_data.get('tiktok_connected'): connected_count += 1
    if user_data.get('meta_connected'): connected_count += 1
    if user_data.get('linkedin_connected'): connected_count += 1
    if user_data.get('youtube_connected'): connected_count += 1
    if user_data.get('threads_connected'): connected_count += 1
    if user_data.get('twitter_connected'): connected_count += 1
    
    if connected_count >= 2:
        return False, "Batas Free Trial tercapai! Akun Free Trial hanya diperbolehkan menautkan maksimal 2 akun sosial media. Silakan upgrade ke akun berbayar."
        
    return True, ""

@oauth_bp.route('/api/disconnect-social', methods=['POST'])
def disconnect_social():
    # SECURITY FIX: Hanya izinkan user yang sedang login di sesi server (Anti-F12 Hijack)
    active_email = session.get('user_email', '').strip().lower()
    if not active_email:
        return jsonify({"success": False, "message": "Autentikasi gagal. Sesi tidak ditemukan."}), 401

    data = request.json or {}
    platform = data.get('platform', '').strip()

    if not platform:
        return jsonify({"success": False, "message": "Data tidak lengkap"}), 400

    email = active_email

    sheet = db.get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            found_idx = -1
            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == email:
                    found_idx = idx + 1
                    break

            if found_idx != -1:
                p = platform.lower()
                if p == 'tiktok':
                    sheet.update_cell(found_idx, 7, "")
                    sheet.update_cell(found_idx, 8, "")
                    sheet.update_cell(found_idx, 9, "")
                elif p in ['facebook', 'instagram']:
                    sheet.update_cell(found_idx, 10, "")
                elif p == 'linkedin':
                    sheet.update_cell(found_idx, 11, "")
                elif p == 'youtube':
                    sheet.update_cell(found_idx, 12, "")
                    sheet.update_cell(found_idx, 13, "")
                elif p == 'threads':
                    sheet.update_cell(found_idx, 14, "")
                elif p in ['twitter', 'x']:
                    sheet.update_cell(found_idx, 15, "")
                
                return jsonify({"success": True, "message": f"Berhasil menghapus token {platform}"})
        except Exception as e:
            print(f"GSheet Disconnect Error: {e}")
            return jsonify({"success": False, "message": "Gagal update database. " + str(e)})
    
    if email in config.user_2fa_store:
        p = platform.lower()
        if p == 'tiktok': config.user_2fa_store[email]['tiktok_connected'] = False
        elif p in ['facebook', 'instagram']: config.user_2fa_store[email]['meta_connected'] = False
        elif p == 'linkedin': config.user_2fa_store[email]['linkedin_connected'] = False
        elif p == 'youtube': config.user_2fa_store[email]['youtube_connected'] = False
        elif p == 'threads': config.user_2fa_store[email]['threads_connected'] = False
        elif p in ['twitter', 'x']: config.user_2fa_store[email]['twitter_connected'] = False
        return jsonify({"success": True, "message": f"Berhasil (Local) menghapus token {platform}"})
        
    return jsonify({"success": False, "message": "Email tidak ditemukan"})

@oauth_bp.route('/api/tiktok-auth-url', methods=['GET'])
def get_tiktok_auth_url():
    email = (session.get('user_email', '') or request.args.get('email', '')).strip().lower()
    can_connect, err_msg = check_trial_social_limit(email)
    if not can_connect:
        return jsonify({"success": False, "message": err_msg}), 400

    redirect_uri = "https://trendoraautomation.my.id/auth/tiktok/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    
    params = {
        "client_key": config.TIKTOK_CLIENT_KEY,
        "response_type": "code",
        "scope": "user.info.basic,video.upload,video.publish",
        "redirect_uri": redirect_uri,
        "state": state
    }
    base_url = "https://www.tiktok.com/v2/auth/authorize/"
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return jsonify({"success": True, "url": full_url})

@oauth_bp.route('/auth/tiktok/callback', methods=['GET'])
def tiktok_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    
    if code and email:
        try:
            token_url = "https://open.tiktokapis.com/v2/oauth/token/"
            payload = {
                "client_key": config.TIKTOK_CLIENT_KEY,
                "client_secret": config.TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "https://trendoraautomation.my.id/auth/tiktok/callback"
            }
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                open_id = res_data.get('open_id')
                refresh_token = res_data.get('refresh_token')
                
                sheet = db.get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            row_idx = idx + 1
                            sheet.update_cell(row_idx, 7, access_token)
                            sheet.update_cell(row_idx, 8, open_id)
                            sheet.update_cell(row_idx, 9, refresh_token)
                            break
        except Exception as e:
            print("TikTok OAuth Error:", e)

    return """
    <html><body><h2 style="color:#34d399;text-align:center;margin-top:50px;">TikTok Connected!</h2>
    <script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'TikTok'}, '*');window.close();}</script>
    </body></html>
    """

@oauth_bp.route('/api/tiktok/creator-info', methods=['GET'])
def get_tiktok_creator_info():
    """
    Mengambil data profil dan permission creator TikTok (Sesuai Poin 1 Content Sharing Guidelines).
    """
    # SECURITY FIX: Utamakan sesi login server, atau validasi API Key terdaftar
    session_email = session.get('user_email', '').strip().lower()
    api_key = (request.headers.get('X-API-Key') or request.args.get('api_key') or '').strip()

    email = None
    if session_email:
        email = session_email
    elif api_key:
        sheet_u = db.get_gsheet()
        if sheet_u:
            try:
                for r in sheet_u.get_all_values()[1:]:
                    if len(r) >= 5 and str(r[4]).strip() == api_key:
                        email = str(r[0]).strip().lower()
                        break
            except Exception:
                pass

    if not email:
        return jsonify({"success": False, "message": "Autentikasi sesi atau API Key valid diperlukan."}), 401

    user_tokens = db.db_get_tiktok_tokens_by_api_key(api_key=api_key, email=email)
    access_token = user_tokens.get('access_token')
    refresh_token = user_tokens.get('refresh_token')
    row_idx = user_tokens.get('row_idx')

    if not access_token and refresh_token:
        from routes.webhook_n8n import refresh_tiktok_token
        access_token = refresh_tiktok_token(refresh_token, row_idx)

    if not access_token:
        return jsonify({
            "success": False,
            "connected": False,
            "message": "Akun TikTok belum terhubung."
        })

    try:
        url = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        req = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        c_data = data.get('data', {})
        nickname = c_data.get('creator_nickname') or "TikTok Creator"
        username = c_data.get('creator_username') or ""
        avatar_url = c_data.get('creator_avatar_url') or ""
        privacy_options = c_data.get('privacy_level_options') or ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"]
        
        return jsonify({
            "success": True,
            "connected": True,
            "creator": {
                "nickname": nickname,
                "username": username,
                "avatar_url": avatar_url,
                "privacy_level_options": privacy_options,
                "comment_disabled": c_data.get('comment_disabled', False),
                "duet_disabled": c_data.get('duet_disabled', False),
                "stitch_disabled": c_data.get('stitch_disabled', False),
                "max_video_post_duration_sec": c_data.get('max_video_post_duration_sec', 600)
            }
        })
    except Exception as e:
        return jsonify({
            "success": True,
            "connected": True,
            "creator": {
                "nickname": "TikTok Creator",
                "username": "creator",
                "avatar_url": "",
                "privacy_level_options": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
                "comment_disabled": False,
                "duet_disabled": False,
                "stitch_disabled": False,
                "max_video_post_duration_sec": 600
            },
            "note": str(e)
        })

@oauth_bp.route('/api/meta-auth-url', methods=['GET'])
def get_meta_auth_url():
    email = (session.get('user_email', '') or request.args.get('email', '')).strip().lower()
    can_connect, err_msg = check_trial_social_limit(email)
    if not can_connect:
        return jsonify({"success": False, "message": err_msg}), 400

    if not config.META_CLIENT_ID:
        return jsonify({
            "success": False, 
            "message": "Meta App ID (META_CLIENT_ID) belum dikonfigurasi di Environment Variables server. Silakan tambahkan META_CLIENT_ID & META_CLIENT_SECRET di dashboard Vercel / server Anda."
        }), 400

    redirect_uri = "https://trendoraautomation.my.id/auth/meta/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    scopes = "pages_show_list,pages_read_engagement,pages_manage_posts,pages_manage_engagement,pages_read_user_content,read_insights,instagram_basic,instagram_content_publish"
    
    params = {
        "client_id": config.META_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scopes,
        "response_type": "code"
    }
    base_url = "https://www.facebook.com/v18.0/dialog/oauth"
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return jsonify({"success": True, "url": full_url})

@oauth_bp.route('/auth/meta/callback', methods=['GET'])
def meta_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    
    if code and email:
        try:
            token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
            payload = {
                "client_id": config.META_CLIENT_ID,
                "client_secret": config.META_CLIENT_SECRET,
                "redirect_uri": "https://trendoraautomation.my.id/auth/meta/callback",
                "code": code
            }
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(token_url, data=data)
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                sheet = db.get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            sheet.update_cell(idx + 1, 10, access_token)
                            break
        except Exception as e:
            print("Meta OAuth Error:", e)

    return """
    <html><body style="background:#0d0a1a;"><h2 style="color:#34d399;text-align:center;margin-top:50px;">Meta Connected!</h2>
    <script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'Meta'}, '*');window.close();}</script>
    </body></html>
    """

@oauth_bp.route('/auth/meta/webhook', methods=['GET', 'POST'])
@oauth_bp.route('/api/meta-webhook', methods=['GET', 'POST'])
@oauth_bp.route('/api/meta/webhook', methods=['GET', 'POST'])
def meta_webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode') or request.args.get('hub_mode')
        token = request.args.get('hub.verify_token') or request.args.get('hub_verify_token')
        challenge = request.args.get('hub.challenge') or request.args.get('hub_challenge')
        
        valid_tokens = {
            "trendora_meta_verify_token_2026",
            "trendora_meta_secret_123",
            str(getattr(config, "META_WEBHOOK_VERIFY_TOKEN", "")).strip()
        }
        
        # Validasi mode subscribe dan token dari Meta Developer Dashboard
        if mode == 'subscribe' and (token in valid_tokens or str(token).strip() in valid_tokens):
            print(f"[Meta Webhook Verified]: challenge={challenge}")
            return Response(challenge, mimetype='text/plain', status=200)
            
        # Toleransi mode subscribe dengan challenge
        if mode == 'subscribe' and challenge:
            print(f"[Meta Webhook Fallback Verified]: token={token}, challenge={challenge}")
            return Response(challenge, mimetype='text/plain', status=200)

        return Response("Forbidden", mimetype='text/plain', status=403)
    elif request.method == 'POST':
        data = request.json or {}
        print("Event Meta Webhook:", json.dumps(data))
        
        # 1. Tangani event 'feed' (Auto-Balas Komen Reels & Post Facebook Page)
        if data.get('object') == 'page':
            for entry in data.get('entry', []):
                page_id = str(entry.get('id', '')).strip()
                for change in entry.get('changes', []):
                    if change.get('field') == 'feed':
                        val = change.get('value', {})
                        item = val.get('item')
                        verb = val.get('verb')
                        
                        # Respon saat ada komentar baru masuk
                        if item == 'comment' and verb == 'add':
                            comment_id = val.get('comment_id')
                            sender_id = str(val.get('sender_id') or val.get('from', {}).get('id', '')).strip()
                            sender_name = str(val.get('sender_name') or val.get('from', {}).get('name') or 'Kak').strip()
                            user_comment = str(val.get('message', '')).strip()
                            post_id = val.get('post_id')
                            
                            # Jangan balas komentar dari halaman sendiri agar tidak terjadi looping
                            if sender_id and page_id and sender_id == page_id:
                                continue
                                
                            if comment_id:
                                auto_reply_to_facebook_comment(page_id, comment_id, sender_name, user_comment, post_id)
                                
        return "EVENT_RECEIVED", 200

def find_meta_page_token(page_id=None, api_key=None, email=None):
    """
    Menemukan Page Access Token Facebook dari database berdasarkan page_id, api_key, atau email.
    """
    token = None
    if api_key or email:
        token = db.db_get_meta_token_by_api_key(api_key, email=email)
        
    if not token:
        sheet = db.get_gsheet()
        if sheet:
            try:
                for row in sheet.get_all_values()[1:]:
                    if len(row) >= 10 and str(row[9]).strip():
                        token = str(row[9]).strip()
                        break
            except Exception:
                pass

    if not token:
        return None, None

    # Periksa apakah token adalah User Token yang memiliki daftar Pages
    try:
        acc_url = f"https://graph.facebook.com/v21.0/me/accounts?access_token={token}"
        with urllib.request.urlopen(urllib.request.Request(acc_url), timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            pages = data.get('data', [])
            if pages:
                if page_id:
                    for p in pages:
                        if str(p.get('id')) == str(page_id):
                            return p.get('access_token'), p.get('id')
                return pages[0].get('access_token'), pages[0].get('id')
    except Exception:
        pass

    # Jika langsung merupakan Page Token
    try:
        me_url = f"https://graph.facebook.com/v21.0/me?access_token={token}"
        with urllib.request.urlopen(urllib.request.Request(me_url), timeout=10) as resp:
            me_data = json.loads(resp.read().decode('utf-8'))
            return token, me_data.get('id')
    except Exception:
        pass

    return token, page_id

def auto_reply_to_facebook_comment(page_id, comment_id, sender_name, user_comment, post_id=None):
    """
    Membalas komentar Facebook otomatis menggunakan Graph API v21.0 dan Gemini AI.
    """
    if not comment_id:
        return False, "comment_id kosong"
        
    page_token, resolved_page_id = find_meta_page_token(page_id=page_id)
    if not page_token:
        print(f"[Meta Auto-Reply]: Tidak menemukan token aktif untuk Page {page_id}")
        return False, "Page token tidak ditemukan"

    # Hasilkan pesan balasan interaktif via Gemini AI
    try:
        from utils.ai_helper import get_ai_chat_response
        ai_prompt = (
            f"Anda adalah admin Facebook Page resmi yang ramah, santai, dan interaktif. "
            f"Penonton ({sender_name}) berkomentar: '{user_comment}'. "
            f"Buat 1 kalimat balasan yang apresiatif, hangat, dan gunakan 1-2 emoji. "
            f"Kirimkan langsung kalimat balasannya saja tanpa tanda petik atau pengantar."
        )
        reply_msg = get_ai_chat_response(ai_prompt)
        if not reply_msg or "Maaf, AI" in reply_msg or "Halo! Terima kasih" in reply_msg:
            reply_msg = f"Halo kak {sender_name}! Makasih banyak udah mampir dan ninggalin jejak ya 🔥 Sukses selalu buat kakak!"
    except Exception:
        reply_msg = f"Halo kak {sender_name}! Terima kasih banyak sudah mampir dan berkomentar ya 🔥 Semoga harimu menyenangkan!"

    # Kirim balasan via Graph API v21.0
    try:
        reply_url = f"https://graph.facebook.com/v21.0/{comment_id}/comments"
        payload = urllib.parse.urlencode({
            'message': reply_msg,
            'access_token': page_token
        }).encode('utf-8')
        req = urllib.request.Request(reply_url, data=payload, method='POST')
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode('utf-8'))
            reply_id = res_data.get('id')
            
        print(f"[Meta Auto-Reply Success]: Berhasil balas komentar {comment_id} (Reply ID: {reply_id})")
        
        # Catat ke sheet Logs
        try:
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            log_id = f"REPLY-{uuid.uuid4().hex[:8].upper()}"
            sheet_logs = db.get_logs_sheet()
            if sheet_logs:
                col_a = sheet_logs.col_values(1)
                next_row = len(col_a) + 1
                details_json = json.dumps({
                    "action": "AUTO_REPLY_FACEBOOK",
                    "comment_id": comment_id,
                    "sender_name": sender_name,
                    "user_comment": user_comment,
                    "reply_sent": reply_msg,
                    "reply_id": reply_id
                })
                row_data = [timestamp, log_id, "SYSTEM_AUTO_REPLY", "facebook", "AUTO_REPLIED", details_json, "Komentar Otomatis Terbalas", post_id or "", reply_msg, ""]
                sheet_logs.update(values=[row_data], range_name=f"A{next_row}:J{next_row}")
        except Exception as e_log:
            print(f"[Meta Auto-Reply Log Error]: {e_log}")
            
        return True, reply_msg
    except Exception as e_post:
        print(f"[Meta Auto-Reply Error]: {e_post}")
        return False, str(e_post)

@oauth_bp.route('/api/meta/insights', methods=['GET', 'POST'])
def get_meta_insights():
    """
    Mengambil data insight performa Meta (Facebook Page & Reels) via Graph API v21.0
    serta memberikan analisis evaluasi algoritma dengan bantuan AI.
    """
    req_data = request.json if request.method == 'POST' and request.is_json else request.args
    object_id = (req_data.get('object_id') or req_data.get('id') or req_data.get('post_id') or req_data.get('reels_id') or '').strip()
    insight_type = req_data.get('type', 'reels').strip().lower()
    email = (session.get('user_email', '') or req_data.get('email', '')).strip().lower()
    api_key = (request.headers.get('X-API-Key') or req_data.get('api_key') or '').strip()

    page_token, page_id = find_meta_page_token(page_id=object_id if insight_type == 'page' else None, api_key=api_key, email=email)
    if not page_token:
        return jsonify({
            "success": False,
            "message": "Token Facebook Page belum terhubung di sistem TRENDORA. Pastikan akun Meta/Facebook sudah terhubung di dashboard."
        }), 400

    target_id = object_id or page_id
    if not target_id:
        return jsonify({
            "success": False,
            "message": "Parameter object_id (ID Reels atau ID Post) harus diisi."
        }), 400

    # 1. INSIGHT LEVEL PAGE
    if insight_type == 'page':
        metrics = "page_post_engagements,page_views_total,page_follows"
        url = f"https://graph.facebook.com/v21.0/{target_id}/insights?metric={metrics}&access_token={page_token}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return jsonify({
                "success": True,
                "type": "page",
                "page_id": target_id,
                "insights": data.get('data', [])
            })
        except urllib.error.HTTPError as he:
            err_body = he.read().decode('utf-8', errors='ignore')
            return jsonify({"success": False, "error": f"[Meta API HTTP {he.code}] {err_body}"}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # 2. STATUS MONETISASI
    elif insight_type == 'monetization':
        url = f"https://graph.facebook.com/v21.0/{page_id}?fields=monetization_status,content_monetization_eligibility&access_token={page_token}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return jsonify({
                "success": True,
                "type": "monetization",
                "page_id": page_id,
                "monetization": data
            })
        except urllib.error.HTTPError as he:
            err_body = he.read().decode('utf-8', errors='ignore')
            return jsonify({"success": False, "error": f"[Meta API HTTP {he.code}] {err_body}"}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # 3. INSIGHT REELS / VIDEO / POST
    else:
        video_info = {}
        try:
            v_url = f"https://graph.facebook.com/v21.0/{target_id}?fields=title,description,created_time,length,views&access_token={page_token}"
            with urllib.request.urlopen(urllib.request.Request(v_url), timeout=10) as v_resp:
                video_info = json.loads(v_resp.read().decode('utf-8'))
        except Exception:
            pass

        metrics = "post_impressions,post_impressions_unique,post_engaged_users,post_video_views,post_video_view_time"
        url = f"https://graph.facebook.com/v21.0/{target_id}/insights?metric={metrics}&access_token={page_token}"
        
        metrics_dict = {}
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for item in data.get('data', []):
                    m_name = item.get('name')
                    values = item.get('values', [])
                    val = values[0].get('value', 0) if values else 0
                    metrics_dict[m_name] = val
        except urllib.error.HTTPError:
            metrics_dict = {
                "post_video_views": video_info.get('views', 0),
                "post_impressions": 0,
                "post_impressions_unique": 0,
                "post_engaged_users": 0,
                "post_video_view_time": 0
            }

        total_views = metrics_dict.get('post_video_views') or video_info.get('views') or 0
        total_reach = metrics_dict.get('post_impressions_unique', 0)
        total_impressions = metrics_dict.get('post_impressions', 0)
        engaged_users = metrics_dict.get('post_engaged_users', 0)
        watch_time_ms = metrics_dict.get('post_video_view_time', 0)
        watch_time_sec = round(watch_time_ms / 1000, 1) if watch_time_ms > 1000 else watch_time_ms
        avg_watch_time = round(watch_time_sec / total_views, 1) if total_views > 0 else 0

        # Evaluasi Algoritma AI (Khusus analisa views rendah / 4 views)
        diagnosis_reasons = []
        recommendations = []

        if total_views < 15:
            diagnosis_reasons.append("Terkunci di Tahap Cold Audience (Pengujian 10-20 Penonton Pertama): Meta menyodorkan video ke segmen kecil penonton. Karena tidak ada lonjakan tontonan >3 detik atau interaksi cepat, sebaran feed otomatis dihentikan.")
        if total_reach > 0 and total_views > 0 and (total_views / total_reach) < 0.35:
            diagnosis_reasons.append("Drop Rate Hook 3 Detik Awal: Penonton langsung melakukan swipe-up sebelum video sempat menyajikan inti topik.")
        if engaged_users == 0:
            diagnosis_reasons.append("Sinyal Interaksi Kosong (Zero Engagement): Belum ada like, komentar, atau share dalam 15-30 menit awal rilis.")

        if not diagnosis_reasons:
            diagnosis_reasons.append("Video memiliki akselerasi distribusi yang sehat. Pertahankan konsistensi!")

        recommendations.append("Pasang Hook Teks Kontras & Padat di detik 0-2 (contoh: 'Jangan lakukan ini saat WFH!' daripada judul biasa).")
        recommendations.append("Tulis pertanyaan pemantik di caption/akhir video untuk mengundang komentar pertama.")
        recommendations.append("Fitur Auto-Reply TRENDORA sekarang aktif: setiap ada komentar masuk akan langsung dibalas AI, memberikan sinyal aktif ke algoritma Meta.")

        return jsonify({
            "success": True,
            "type": "reels",
            "object_id": target_id,
            "video_info": video_info,
            "metrics": {
                "views": total_views,
                "reach": total_reach,
                "impressions": total_impressions,
                "engaged_users": engaged_users,
                "total_watch_time_sec": watch_time_sec,
                "avg_watch_time_sec": avg_watch_time
            },
            "ai_evaluation": {
                "diagnosis": diagnosis_reasons,
                "recommendations": recommendations,
                "status": "Needs Optimization" if total_views < 50 else "Good Traction"
            }
        })

@oauth_bp.route('/api/twitter-webhook', methods=['GET', 'POST'], strict_slashes=False)
def twitter_webhook():
    if request.method == 'GET':
        crc_token = request.args.get('crc_token')
        if crc_token:
            secret = config.TWITTER_CLIENT_SECRET or ""
            sha256_hash_digest = hmac.new(secret.encode('utf-8'), msg=crc_token.encode('utf-8'), digestmod=hashlib.sha256).digest()
            response_token = 'sha256=' + base64.b64encode(sha256_hash_digest).decode('utf-8')
            return jsonify({"response_token": response_token}), 200
        return "Bad Request", 400
    elif request.method == 'POST':
        print("Event Twitter Webhook:", request.json)
        return "EVENT_RECEIVED", 200

@oauth_bp.route('/api/twitter-auth-url', methods=['GET'])
def get_twitter_auth_url():
    email = (session.get('user_email', '') or request.args.get('email', '')).strip().lower()
    can_connect, err_msg = check_trial_social_limit(email)
    if not can_connect:
        return jsonify({"success": False, "message": err_msg}), 400

    state = f"{uuid.uuid4().hex[:8]}|{email}"
    params = {
        "response_type": "code",
        "client_id": config.TWITTER_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": "https://trendoraautomation.my.id/auth/twitter/callback",
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": state,
        "code_challenge": "trendora_twitter_challenge_123",
        "code_challenge_method": "plain"
    }
    return jsonify({"success": True, "url": f"https://twitter.com/i/oauth2/authorize?{urllib.parse.urlencode(params)}"})

@oauth_bp.route('/auth/twitter/callback', methods=['GET'])
def twitter_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    if code and email:
        try:
            payload = {
                "code": code,
                "grant_type": "authorization_code",
                "client_id": config.TWITTER_CLIENT_ID,
                "redirect_uri": "https://trendoraautomation.my.id/auth/twitter/callback",
                "code_verifier": "trendora_twitter_challenge_123"
            }
            auth_str = f"{config.TWITTER_CLIENT_ID}:{config.TWITTER_CLIENT_SECRET}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request("https://api.twitter.com/2/oauth2/token", data=data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            req.add_header('Authorization', f'Basic {b64_auth}')
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                sheet = db.get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            sheet.update_cell(idx + 1, 15, access_token)
                            break
        except Exception as e:
            print("Twitter OAuth Error:", e)

    return """<html><body style="background:#0d0a1a;"><h2 style="color:#1d9bf0;text-align:center;margin-top:50px;">Twitter/X Connected!</h2><script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'Twitter'}, '*');window.close();}</script></body></html>"""

@oauth_bp.route('/api/linkedin-auth-url', methods=['GET'])
def get_linkedin_auth_url():
    email = (session.get('user_email', '') or request.args.get('email', '')).strip().lower()
    can_connect, err_msg = check_trial_social_limit(email)
    if not can_connect:
        return jsonify({"success": False, "message": err_msg}), 400

    redirect_uri = "https://trendoraautomation.my.id/auth/linkedin/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    params = {
        "response_type": "code",
        "client_id": config.LINKEDIN_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": redirect_uri,
        "scope": "openid profile email w_member_social",
        "state": state
    }
    return jsonify({"success": True, "url": f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"})

@oauth_bp.route('/auth/linkedin/callback', methods=['GET'])
def linkedin_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    if code and email:
        try:
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": config.LINKEDIN_CLIENT_ID,
                "client_secret": config.LINKEDIN_CLIENT_SECRET,
                "redirect_uri": "https://trendoraautomation.my.id/auth/linkedin/callback"
            }
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request("https://www.linkedin.com/oauth/v2/accessToken", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                sheet = db.get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            sheet.update_cell(idx + 1, 11, access_token)
                            break
        except Exception as e:
            print("LinkedIn OAuth Error:", e)

    return """<html><body style="background:#0d0a1a;"><h2 style="color:#34d399;text-align:center;margin-top:50px;">LinkedIn Connected!</h2><script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'LinkedIn'}, '*');window.close();}</script></body></html>"""

@oauth_bp.route('/api/youtube-auth-url', methods=['GET'])
def get_youtube_auth_url():
    email = (session.get('user_email', '') or request.args.get('email', '')).strip().lower()
    can_connect, err_msg = check_trial_social_limit(email)
    if not can_connect:
        return jsonify({"success": False, "message": err_msg}), 400

    state = f"{uuid.uuid4().hex[:8]}|{email}"
    params = {
        "client_id": config.GOOGLE_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": "https://trendoraautomation.my.id/auth/youtube/callback",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload",
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    return jsonify({"success": True, "url": f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"})

@oauth_bp.route('/auth/youtube/callback', methods=['GET'])
def youtube_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    if code and email:
        try:
            payload = {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "https://trendoraautomation.my.id/auth/youtube/callback"
            }
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                refresh_token = res_data.get('refresh_token', '')
                sheet = db.get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            row_idx = idx + 1
                            sheet.update_cell(row_idx, 12, access_token)
                            if refresh_token:
                                sheet.update_cell(row_idx, 13, refresh_token)
                            break
        except Exception as e:
            print("YouTube OAuth Error:", e)

    return """<html><body style="background:#0d0a1a;"><h2 style="color:#ff0000;text-align:center;margin-top:50px;">YouTube Connected!</h2><script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'YouTube'}, '*');window.close();}</script></body></html>"""

@oauth_bp.route('/api/threads-auth-url', methods=['GET'])
def get_threads_auth_url():
    email = (session.get('user_email', '') or request.args.get('email', '')).strip().lower()
    can_connect, err_msg = check_trial_social_limit(email)
    if not can_connect:
        return jsonify({"success": False, "message": err_msg}), 400

    state = f"{uuid.uuid4().hex[:8]}|{email}"
    params = {
        "client_id": config.THREADS_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": "https://trendoraautomation.my.id/auth/threads/callback",
        "scope": "threads_basic,threads_content_publish",
        "response_type": "code",
        "state": state
    }
    return jsonify({"success": True, "url": f"https://threads.net/oauth/authorize?{urllib.parse.urlencode(params)}"})

@oauth_bp.route('/auth/threads/callback', methods=['GET'])
def threads_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    if code and email:
        try:
            payload = {
                "client_id": config.THREADS_CLIENT_ID,
                "client_secret": config.THREADS_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": "https://trendoraautomation.my.id/auth/threads/callback",
                "code": code
            }
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request("https://graph.threads.net/oauth/access_token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                sheet = db.get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            sheet.update_cell(idx + 1, 14, access_token)
                            break
        except Exception as e:
            print("Threads OAuth Error:", e)

    return """<html><body style="background:#0d0a1a;"><h2 style="color:#ffffff;text-align:center;margin-top:50px;">Threads Connected!</h2><script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'Threads'}, '*');window.close();}</script></body></html>"""


@oauth_bp.route('/api/tiktok/direct-share', methods=['POST'])
def direct_share_to_tiktok():
    """
    Endpoint resmi untuk fitur 'Studio Share to TikTok' di Dashboard Trendora.
    Memenuhi standar UX Guidelines Poin 3 & 4 TikTok Developer Review:
    - Menerima aksi klik eksplisit dari pengguna untuk membagikan video.
    - Menerima file video upload langsung (.mp4/.mov) atau media_url.
    - Menerapkan parameter kustomisasi privasi & interaksi (komentar, duet, stitch).
    - Menghasilkan respon transparan untuk feedback indikator upload & konfirmasi sukses.
    """
    from routes.webhook_n8n import upload_video_to_tiktok
    
    # 1. Dapatkan identitas pengguna terotentikasi (Sesi server terenkripsi atau API Key terdaftar)
    session_email = session.get('user_email', '').strip().lower()
    api_key = (request.headers.get('X-API-Key') or request.form.get('api_key') or '').strip()

    email = None
    if session_email:
        email = session_email
    elif api_key:
        sheet_u = db.get_gsheet()
        if sheet_u:
            try:
                for r in sheet_u.get_all_values()[1:]:
                    if len(r) >= 5 and str(r[4]).strip() == api_key:
                        email = str(r[0]).strip().lower()
                        break
            except Exception:
                pass

    if not email:
        return jsonify({
            "success": False,
            "error_code": "AUTH_REQUIRED",
            "message": "Autentikasi gagal. Sesi login pengguna atau API Key valid tidak ditemukan."
        }), 401
        
    # 2. Ambil token TikTok pengguna dari database
    user_tokens = db.db_get_tiktok_tokens_by_api_key(api_key=api_key, email=email)
    access_token = user_tokens.get('access_token')
    refresh_token = user_tokens.get('refresh_token')
    row_idx = user_tokens.get('row_idx')
    
    if not access_token and not refresh_token:
        return jsonify({
            "success": False,
            "error_code": "TIKTOK_NOT_CONNECTED",
            "message": "Akun TikTok belum terhubung! Silakan klik 'Hubungkan Akun TikTok' terlebih dahulu untuk memberikan otorisasi."
        }), 400
        
    # 3. Tangani berkas video (Upload File Langsung atau Media URL)
    video_bytes = None
    media_url = None
    
    if 'video_file' in request.files:
        v_file = request.files['video_file']
        if v_file and v_file.filename != '':
            video_bytes = v_file.read()
            if len(video_bytes) == 0:
                return jsonify({
                    "success": False,
                    "error_code": "EMPTY_FILE",
                    "message": "Berkas video yang diunggah kosong (0 bytes)."
                }), 400
    
    if not video_bytes:
        media_url = request.form.get('media_url', '').strip()
        if not media_url:
            return jsonify({
                "success": False,
                "error_code": "NO_MEDIA",
                "message": "Harap pilih file video (.mp4) atau masukkan URL video sebelum membagikan ke TikTok."
            }), 400

    # 4. Ambil opsi kustomisasi (Poin 3: Kontrol & Kustomisasi Pengguna)
    caption = request.form.get('caption', 'Video via Trendora Automation 🚀').strip()
    privacy_level = request.form.get('privacy_level', 'PUBLIC_TO_EVERYONE').strip()
    disable_comment = request.form.get('disable_comment', 'false').lower() == 'true'
    disable_duet = request.form.get('disable_duet', 'false').lower() == 'true'
    disable_stitch = request.form.get('disable_stitch', 'false').lower() == 'true'
    brand_organic_toggle = request.form.get('brand_organic_toggle', 'false').lower() == 'true'
    brand_content_toggle = request.form.get('brand_content_toggle', 'false').lower() == 'true'

    # 5. Jalankan proses pengunggahan ke TikTok via Content Posting API v2
    try:
        is_ok, res_dict = upload_video_to_tiktok(
            access_token=access_token,
            refresh_token=refresh_token,
            media_url=media_url,
            caption=caption,
            privacy_level=privacy_level,
            row_idx=row_idx,
            video_bytes=video_bytes,
            disable_duet=disable_duet,
            disable_comment=disable_comment,
            disable_stitch=disable_stitch,
            brand_organic_toggle=brand_organic_toggle,
            brand_content_toggle=brand_content_toggle
        )
        
        if is_ok:
            publish_id = res_dict.get('publish_id', '')
            # Catat aktivitas ke audit logs
            try:
                sheet_logs = db.get_logs_sheet()
                if sheet_logs:
                    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    sheet_logs.append_row([
                        now_str,
                        email or "Web Studio",
                        "Direct Share to TikTok",
                        "SUCCESS",
                        f"Publish ID: {publish_id} | Privasi: {privacy_level} | BrandOrganic: {brand_organic_toggle} | BrandedContent: {brand_content_toggle}"
                    ])
            except Exception:
                pass

            return jsonify({
                "success": True,
                "publish_id": publish_id,
                "privacy_level": privacy_level,
                "brand_organic_toggle": brand_organic_toggle,
                "brand_content_toggle": brand_content_toggle,
                "message": "Video berhasil dikirim dan dipublikasikan ke akun TikTok Anda!",
                "details": res_dict
            })
        else:
            err_msg = res_dict.get('tiktok_error', 'Gagal mengunggah video ke server TikTok.')
            return jsonify({
                "success": False,
                "error_code": "TIKTOK_API_ERROR",
                "message": err_msg,
                "details": res_dict
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error_code": "SERVER_EXCEPTION",
            "message": f"Terjadi kesalahan internal saat memproses video: {str(e)}"
        }), 500