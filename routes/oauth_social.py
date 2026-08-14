import os
import sys

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Blueprint, request, jsonify
import urllib.request
import urllib.parse
import uuid
import json
import base64
import hmac
import hashlib

import config
from utils import database as db
from routes.auth import check_user_trial_status

oauth_bp = Blueprint('oauth_social', __name__)

def check_trial_social_limit(email):
    """
    Memeriksa apakah akun trial sudah melebihi batas 2 sosial media atau sudah expired.
    Return (can_connect: bool, error_message: str)
    """
    if not email:
        return False, "Email pengguna tidak valid."
        
    user_data = db.db_get_user(email)
    if not user_data:
        return False, "User tidak ditemukan."
        
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
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    platform = data.get('platform', '').strip()

    if not email or not platform:
        return jsonify({"success": False, "message": "Data tidak lengkap"})

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
    email = request.args.get('email', '').strip()
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

@oauth_bp.route('/api/meta-auth-url', methods=['GET'])
def get_meta_auth_url():
    email = request.args.get('email', '').strip()
    can_connect, err_msg = check_trial_social_limit(email)
    if not can_connect:
        return jsonify({"success": False, "message": err_msg}), 400

    redirect_uri = "https://trendoraautomation.my.id/auth/meta/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    scopes = "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"
    
    params = {
        "client_id": config.META_CLIENT_ID or "DUMMY_ID",
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

@oauth_bp.route('/api/meta-webhook', methods=['GET', 'POST'])
def meta_webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode and token and mode == 'subscribe' and token == config.META_WEBHOOK_VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403
    elif request.method == 'POST':
        print("Event Meta Webhook:", request.json)
        return "EVENT_RECEIVED", 200

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
    email = request.args.get('email', '').strip()
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
    email = request.args.get('email', '').strip()
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
    email = request.args.get('email', '').strip()
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
    email = request.args.get('email', '').strip()
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