from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import urllib.request
import urllib.parse
import urllib.error
import json
import base64
import uuid
import re
import hmac
import hashlib
import time
import struct
import os
import smtplib
import tempfile
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Response, stream_with_context, redirect

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

app = Flask(__name__)
CORS(app) 


# ==========================================
# KONFIGURASI DATABASE GOOGLE SHEETS
# ==========================================
GOOGLE_SHEET_ID = "1P0zTEwtMmWfxhHAY6-QbQd5to6Id1rzazgel-PiSJwI" 
SERVICE_ACCOUNT_FILE = "service_account.json" 

user_2fa_store = {}

# KONFIGURASI TIKTOK DEVELOPER
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET")

# KONFIGURASI META (FACEBOOK & INSTAGRAM)
META_CLIENT_ID = os.environ.get("META_CLIENT_ID")
META_CLIENT_SECRET = os.environ.get("META_CLIENT_SECRET")
META_WEBHOOK_VERIFY_TOKEN = os.environ.get("META_WEBHOOK_VERIFY_TOKEN", "trendora_meta_secret_123")

# KONFIGURASI LINKEDIN
LINKEDIN_CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")

# KONFIGURASI YOUTUBE / GOOGLE
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# KONFIGURASI THREADS
THREADS_CLIENT_ID = os.environ.get("THREADS_CLIENT_ID")
THREADS_CLIENT_SECRET = os.environ.get("THREADS_CLIENT_SECRET")

# KONFIGURASI TWITTER
TWITTER_CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET")


def get_gsheet():
    """Koneksi ke Google Sheets (Sheet Utama)."""
    if not HAS_GSPREAD:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if env_creds:
            creds_dict = json.loads(env_creds)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        return sheet
    except Exception as e:
        print(f"GSheets Connection Error: {e} (Menggunakan fallback memori)")
        return None

def get_logs_sheet():
    """Koneksi ke Google Sheets khusus tab 'Logs'."""
    if not HAS_GSPREAD:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if env_creds:
            creds_dict = json.loads(env_creds)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        doc = client.open_by_key(GOOGLE_SHEET_ID)
        
        sheet = None
        worksheets = doc.worksheets()
        for s in worksheets:
            s_title = s.title.lower()
            if "log" in s_title or "aktivitas" in s_title or "aktifitas" in s_title:
                sheet = s
                break
        if not sheet and len(worksheets) > 1:
            sheet = worksheets[1]
        if not sheet:
            sheet = doc.add_worksheet(title="Logs", rows="1000", cols="10")
            sheet.append_row(["Timestamp", "LogID", "APIKey", "Platform", "Status", "Details", "Keterangan", "MediaURL", "Caption", "Hashtag"])
            
        return sheet
    except Exception as e:
        print(f"GSheets Logs Connection Error: {e}")
        return None

def db_get_user(email):
    """Ambil data user dari Google Sheets (scan dari BAWAH agar selalu dapat yg terbaru)."""
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) > 0 and str(row[0]).strip().lower() == email:
                        return {
                            'email': str(row[0]).strip().lower(),
                            'secret': str(row[1]) if len(row) > 1 else '',
                            'is_linked': str(row[2]).lower() == 'true' if len(row) > 2 else False,
                            'name': str(row[3]) if len(row) > 3 else '',
                            'api_key': str(row[4]) if len(row) > 4 else '',
                            'status': str(row[5]) if len(row) > 5 else '',
                            'tiktok_connected': bool(str(row[6]).strip()) if len(row) > 6 else False,
                            'meta_connected': bool(str(row[9]).strip()) if len(row) > 9 else False,
                            'linkedin_connected': bool(str(row[10]).strip()) if len(row) > 10 else False,
                            'youtube_connected': bool(str(row[11]).strip()) if len(row) > 11 else False,
                            'threads_connected': bool(str(row[13]).strip()) if len(row) > 13 else False,
                            'twitter_connected': bool(str(row[14]).strip()) if len(row) > 14 else False,
                            'row_idx': idx + 1  
                        }
            return None
        except Exception as e:
            print(f"GSheet Read Error: {e}")
            return None
            
    if email in user_2fa_store:
        user_data = user_2fa_store[email]
        user_data['tiktok_connected'] = user_data.get('tiktok_connected', False)
        return user_data
    return None

def db_save_user(email, secret, is_linked, name="", api_key="", status=""):
    """Simpan data (scan dari BAWAH)."""
    sheet = get_gsheet()
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
                sheet.update_cell(found_idx, 2, secret)
                sheet.update_cell(found_idx, 3, str(is_linked))
                if name: sheet.update_cell(found_idx, 4, name)
                if api_key: sheet.update_cell(found_idx, 5, api_key)
                if status: sheet.update_cell(found_idx, 6, status)
            else:
                sheet.append_row([email, secret, str(is_linked), name, api_key, status])
            return
        except Exception as e:
            print(f"GSheet Write Error: {e}")
    user_2fa_store[email] = {
        'secret': secret, 'is_linked': is_linked, 'name': name, 'api_key': api_key, 'status': status
    }

def db_get_tiktok_tokens_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return {
                        'access_token': row[6] if len(row) >= 7 else None,
                        'open_id': row[7] if len(row) >= 8 else None
                    }
        except Exception as e:
            print(f"GSheet Get Tokens Error: {e}")
    return {}

def db_get_meta_token_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return row[9] if len(row) >= 10 else None
        except Exception as e:
            print(f"GSheet Get Meta Token Error: {e}")
    return None

def db_get_linkedin_token_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return row[10] if len(row) >= 11 else None
        except Exception as e:
            print(f"GSheet Get LinkedIn Token Error: {e}")
    return None

def db_get_youtube_tokens_by_api_key(api_key):
    """Ambil Access dan Refresh Token YouTube dari GSheet (Kolom L & M)."""
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return {
                        'access_token': row[11] if len(row) >= 12 else None,
                        'refresh_token': row[12] if len(row) >= 13 else None
                    }
        except Exception as e:
            print(f"GSheet Get YouTube Token Error: {e}")
    return {}

def db_get_threads_token_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return row[13] if len(row) >= 14 else None
        except Exception as e:
            print(f"GSheet Get Threads Token Error: {e}")
    return None

def db_get_twitter_token_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return row[14] if len(row) >= 15 else None
        except Exception as e:
            print(f"GSheet Get Twitter Token Error: {e}")
    return None


# ==========================================
# KONFIGURASI SMTP EMAIL (GMAIL)
# ==========================================
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "trendoraautomation@gmail.com") 
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "") 

def send_email_qr(recipient_email, qr_url, secret):
    if not SMTP_PASSWORD: return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Kode QR Google Authenticator - TRENDORA"
    msg["From"] = f"TRENDORA Security <{SMTP_EMAIL}>"
    msg["To"] = recipient_email
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #333; background-color: #0f1524; color: #fff; border-radius: 10px;">
      <h2 style="color: #ec4899; text-align: center;">Reset 2FA Google Authenticator</h2>
      <p style="color: #d1d5db;">Silakan scan QR Code di bawah ini menggunakan aplikasi Google Authenticator:</p>
      <div style="text-align: center; margin: 20px 0;"><img src="{qr_url}" alt="QR Code" width="200" height="200"></div>
      <p style="color: #d1d5db; text-align: center;">Kunci manual: <strong>{secret}</strong></p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

# ==========================================
# LOGIKA TOTP (Google Authenticator)
# ==========================================
def generate_base32_secret():
    bytes_secret = os.urandom(10)
    return base64.b32encode(bytes_secret).decode('utf-8').replace('=', '')

def get_totp_token(secret, intervals_no=None):
    if intervals_no is None: intervals_no = int(time.time()) // 30
    missing_padding = len(secret) % 8
    if missing_padding != 0: secret += '=' * (8 - missing_padding)
    key = base64.b32decode(secret, casefold=True)
    msg = struct.pack(">Q", intervals_no)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 15
    h = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
    return str(h).zfill(6)

def verify_totp(secret, token):
    if not secret or not token: return False
    curr_interval = int(time.time()) // 30
    for delta in [-1, 0, 1]:
        if get_totp_token(secret, curr_interval + delta) == str(token).strip():
            return True
    return False

# ==========================================
# KONFIGURASI MIDTRANS (PRODUCTION)
# ==========================================
MIDTRANS_API_URL = "https://app.midtrans.com/snap/v1/transactions"
MIDTRANS_SERVER_KEY = os.environ.get("MIDTRANS_SERVER_KEY", "Mid-server-zF-SefFUBo7r1t-qcRPzdBEr_DUMMY")

# ==========================================
# FLASK ROUTES (Frontend)
# ==========================================
@app.route('/')
def index(): return render_template('index.html')

@app.route('/login')
def login_page(): return render_template('login.html')

@app.route('/checkout')
def checkout_page(): return render_template('checkout.html')

@app.route('/dashboard')
def dashboard_page(): return render_template('dashboard.html')

@app.route('/webhook')
def webhook_page(): return render_template('webhook.html')

@app.route('/tos')
def tos_page(): return render_template('tos.html')

@app.route('/privacy')
def privacy_page(): return render_template('privacy.html')

@app.route('/data-deletion')
def data_deletion_page(): 
    return render_template('data_deletion_page.html')


# ==========================================
# AUTHENTICATION & API KEY ROUTES
# ==========================================
@app.route('/api/request-otp', methods=['POST'])
def request_otp():
    email = request.json.get('email', '').strip().lower()
    if not email: return jsonify({"success": False, "message": "Email wajib diisi!"})
    user_data = db_get_user(email)
    if not user_data: return jsonify({"success": False, "message": "Email belum terdaftar!"})
    
    secret = user_data['secret']
    is_linked = user_data['is_linked']
    
    if not is_linked:
        issuer = "TRENDORA"
        totp_uri = f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}"
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(totp_uri)}"
        return jsonify({"success": True, "is2faLinked": False, "qrCodeUrl": qr_code_url})
    else:
        return jsonify({"success": True, "is2faLinked": True})

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp_route():
    email = request.json.get('email', '').strip().lower()
    otp = request.json.get('otp', '').strip()
    if not email or not otp: return jsonify({"success": False, "message": "Data tidak lengkap!"})
        
    user_data = db_get_user(email)
    if not user_data: return jsonify({"success": False, "message": "Email belum terdaftar!"})
        
    is_valid = verify_totp(user_data['secret'], otp)
    if is_valid:
        name = user_data.get('name') or email.split('@')[0].capitalize()
        api_key = user_data.get('api_key') or "-"
        status = user_data.get('status') or "Active"
        
        if not user_data.get('is_linked'):
            db_save_user(email, user_data['secret'], True, name, api_key, status)
            
        status_lower = status.lower()
        is_paid_user = any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"])
        
        # CEK KONEKSI PLATFORM
        connected_platforms = []
        if user_data.get('tiktok_connected'):
            connected_platforms.append('TikTok')
        if user_data.get('meta_connected'):
            connected_platforms.append('Facebook')
            connected_platforms.append('Instagram')
        if user_data.get('linkedin_connected'):
            connected_platforms.append('LinkedIn')
        if user_data.get('youtube_connected'):
            connected_platforms.append('YouTube')
        if user_data.get('threads_connected'):
            connected_platforms.append('Threads')
        if user_data.get('twitter_connected'):
            connected_platforms.append('Twitter')
        
        return jsonify({
            "success": True, 
            "user": {
                "name": name, 
                "email": email, 
                "apiKey": api_key, 
                "status": status, 
                "isPaid": is_paid_user,
                "connectedPlatforms": connected_platforms
            }
        })
    return jsonify({"success": False, "message": "OTP salah/kadaluarsa!"})

@app.route('/api/reset-2fa-qr', methods=['POST'])
def reset_2fa_qr():
    email = request.json.get('email', '').strip().lower()
    old_data = db_get_user(email)
    if not old_data: return jsonify({"success": False, "message": "Email tidak ditemukan!"})
    
    new_secret = generate_base32_secret()
    db_save_user(email, new_secret, False, old_data.get('name', ''), old_data.get('api_key', ''), old_data.get('status', ''))
    return jsonify({"success": True, "message": "Reset berhasil."})

@app.route('/api/register-trial', methods=['POST'])
def register_trial():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', 'User').strip()
    
    existing_user = db_get_user(email)
    if existing_user: return jsonify({"success": False, "message": "Email sudah terdaftar!"})
    
    new_secret = generate_base32_secret()
    db_save_user(email, new_secret, False, name, "-", "Active (7-Day Free Trial - View Only)")
    return jsonify({"success": True, "message": "Registrasi berhasil", "user": {"name": name, "email": email, "apiKey": "-", "isPaid": False}})

@app.route('/api/generate-api-key', methods=['POST'])
def generate_api_key_route():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    user_data = db_get_user(email)
    if not user_data: return jsonify({"success": False})

    status_lower = user_data.get('status', '').lower()
    is_paid_user = any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"])

    if not is_paid_user:
        return jsonify({"success": False, "isPaid": False, "message": "Akun Free Trial, upgrade untuk unlock!"})

    new_api_key = "TREND_" + uuid.uuid4().hex[:12].upper()
    db_save_user(email, user_data['secret'], user_data['is_linked'], user_data.get('name', ''), new_api_key, user_data.get('status', ''))
    return jsonify({"success": True, "isPaid": True, "apiKey": new_api_key})

@app.route('/api/me', methods=['POST'])
def get_me():
    email = request.json.get('email', '').strip().lower()
    if not email: return jsonify({"success": False})
    
    user_data = db_get_user(email)
    if not user_data: return jsonify({"success": False})
    
    connected_platforms = []
    if user_data.get('tiktok_connected'):
        connected_platforms.append('TikTok')
    if user_data.get('meta_connected'):
        connected_platforms.append('Facebook')
        connected_platforms.append('Instagram')
    if user_data.get('linkedin_connected'):
        connected_platforms.append('LinkedIn')
    if user_data.get('youtube_connected'):
        connected_platforms.append('YouTube')
    if user_data.get('threads_connected'):
        connected_platforms.append('Threads')
    if user_data.get('twitter_connected'):
        connected_platforms.append('Twitter')
        
    status_lower = user_data.get('status', '').lower()
    is_paid_user = any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"])
    
    return jsonify({
        "success": True,
        "user": {
            "name": user_data.get('name', ''),
            "email": email,
            "apiKey": user_data.get('api_key', '-'),
            "status": user_data.get('status', ''),
            "isPaid": is_paid_user,
            "connectedPlatforms": connected_platforms
        }
    })


# ==========================================
# REAL TIKTOK OAUTH
# ==========================================
@app.route('/api/tiktok-auth-url', methods=['GET'])
def get_tiktok_auth_url():
    email = request.args.get('email', '').strip()
    redirect_uri = "https://trendoraautomation.my.id/auth/tiktok/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "response_type": "code",
        "scope": "user.info.basic,video.upload,video.publish",
        "redirect_uri": redirect_uri,
        "state": state
    }
    base_url = "https://www.tiktok.com/v2/auth/authorize/"
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return jsonify({"success": True, "url": full_url})

@app.route('/auth/tiktok/callback', methods=['GET'])
def tiktok_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    
    if code and email:
        try:
            token_url = "https://open.tiktokapis.com/v2/oauth/token/"
            payload = {
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
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
                
                sheet = get_gsheet()
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

# ==========================================
# REAL META (FB & IG) OAUTH
# ==========================================
@app.route('/api/meta-auth-url', methods=['GET'])
def get_meta_auth_url():
    email = request.args.get('email', '').strip()
    redirect_uri = "https://trendoraautomation.my.id/auth/meta/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    
    scopes = "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"
    
    params = {
        "client_id": META_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scopes,
        "response_type": "code"
    }
    base_url = "https://www.facebook.com/v18.0/dialog/oauth"
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return jsonify({"success": True, "url": full_url})

@app.route('/auth/meta/callback', methods=['GET'])
def meta_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    
    if code and email:
        try:
            token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
            payload = {
                "client_id": META_CLIENT_ID,
                "client_secret": META_CLIENT_SECRET,
                "redirect_uri": "https://trendoraautomation.my.id/auth/meta/callback",
                "code": code
            }
            
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(token_url, data=data)
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                
                sheet = get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            row_idx = idx + 1
                            sheet.update_cell(row_idx, 10, access_token)
                            break
        except Exception as e:
            print("Meta OAuth Error:", e)

    return """
    <html><body style="background:#0d0a1a;"><h2 style="color:#34d399;text-align:center;margin-top:50px;">Meta (Facebook & IG) Connected!</h2>
    <script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'Meta'}, '*');window.close();}</script>
    </body></html>
    """

# ==========================================
# META WEBHOOK (VERIFIKASI & PENERIMA EVENT)
# ==========================================
@app.route('/api/meta-webhook', methods=['GET', 'POST'])
def meta_webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == META_WEBHOOK_VERIFY_TOKEN:
                return challenge, 200
            else:
                return "Forbidden", 403
        return "Bad Request", 400

    elif request.method == 'POST':
        payload = request.json
        print("Menerima Event dari Meta Webhook:", payload)
        return "EVENT_RECEIVED", 200

# ==========================================
# TWITTER WEBHOOK (CRC VERIFICATION)
# ==========================================
@app.route('/api/twitter-webhook', methods=['GET', 'POST'], strict_slashes=False)
def twitter_webhook():
    if request.method == 'GET':
        crc_token = request.args.get('crc_token')
        if crc_token:
            secret = TWITTER_CLIENT_SECRET or ""
            sha256_hash_digest = hmac.new(
                secret.encode('utf-8'),
                msg=crc_token.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            
            response_token = 'sha256=' + base64.b64encode(sha256_hash_digest).decode('utf-8')
            return jsonify({"response_token": response_token}), 200
        return "Bad Request", 400

    elif request.method == 'POST':
        payload = request.json
        print("Menerima Event dari Twitter Webhook:", payload)
        return "EVENT_RECEIVED", 200

# ==========================================
# REAL LINKEDIN OAUTH
# ==========================================
@app.route('/api/linkedin-auth-url', methods=['GET'])
def get_linkedin_auth_url():
    email = request.args.get('email', '').strip()
    redirect_uri = "https://trendoraautomation.my.id/auth/linkedin/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    
    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": redirect_uri,
        "scope": "openid profile email w_member_social",
        "state": state
    }
    base_url = "https://www.linkedin.com/oauth/v2/authorization"
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return jsonify({"success": True, "url": full_url})

@app.route('/auth/linkedin/callback', methods=['GET'])
def linkedin_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    
    if code and email:
        try:
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
                "redirect_uri": "https://trendoraautomation.my.id/auth/linkedin/callback"
            }
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                
                sheet = get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            row_idx = idx + 1
                            sheet.update_cell(row_idx, 11, access_token)
                            break
        except Exception as e:
            print("LinkedIn OAuth Error:", e)

    return """
    <html><body style="background:#0d0a1a;"><h2 style="color:#34d399;text-align:center;margin-top:50px;">LinkedIn Connected!</h2>
    <script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'LinkedIn'}, '*');window.close();}</script>
    </body></html>
    """

# ==========================================
# REAL YOUTUBE (GOOGLE) OAUTH
# ==========================================
@app.route('/api/youtube-auth-url', methods=['GET'])
def get_youtube_auth_url():
    email = request.args.get('email', '').strip()
    redirect_uri = "https://trendoraautomation.my.id/auth/youtube/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    
    params = {
        "client_id": GOOGLE_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload",
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return jsonify({"success": True, "url": full_url})

@app.route('/auth/youtube/callback', methods=['GET'])
def youtube_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    
    if code and email:
        try:
            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "https://trendoraautomation.my.id/auth/youtube/callback"
            }
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                refresh_token = res_data.get('refresh_token', '')
                
                sheet = get_gsheet()
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

    return """
    <html><body style="background:#0d0a1a;"><h2 style="color:#ff0000;text-align:center;margin-top:50px;">YouTube Connected!</h2>
    <script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'YouTube'}, '*');window.close();}</script>
    </body></html>
    """

# ==========================================
# REAL THREADS OAUTH
# ==========================================
@app.route('/api/threads-auth-url', methods=['GET'])
def get_threads_auth_url():
    email = request.args.get('email', '').strip()
    redirect_uri = "https://trendoraautomation.my.id/auth/threads/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    
    params = {
        "client_id": THREADS_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": redirect_uri,
        "scope": "threads_basic,threads_content_publish",
        "response_type": "code",
        "state": state
    }
    base_url = "https://threads.net/oauth/authorize"
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return jsonify({"success": True, "url": full_url})

@app.route('/auth/threads/callback', methods=['GET'])
def threads_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    
    if code and email:
        try:
            token_url = "https://graph.threads.net/oauth/access_token"
            payload = {
                "client_id": THREADS_CLIENT_ID,
                "client_secret": THREADS_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": "https://trendoraautomation.my.id/auth/threads/callback",
                "code": code
            }
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                
                sheet = get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            row_idx = idx + 1
                            sheet.update_cell(row_idx, 14, access_token)
                            break
        except Exception as e:
            print("Threads OAuth Error:", e)

    return """
    <html><body style="background:#0d0a1a;"><h2 style="color:#ffffff;text-align:center;margin-top:50px;">Threads Connected!</h2>
    <script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'Threads'}, '*');window.close();}</script>
    </body></html>
    """

# ==========================================
# REAL TWITTER (X) OAUTH 2.0
# ==========================================
@app.route('/api/twitter-auth-url', methods=['GET'])
def get_twitter_auth_url():
    email = request.args.get('email', '').strip()
    redirect_uri = "https://trendoraautomation.my.id/auth/twitter/callback"
    state = f"{uuid.uuid4().hex[:8]}|{email}"
    
    params = {
        "response_type": "code",
        "client_id": TWITTER_CLIENT_ID or "DUMMY_ID",
        "redirect_uri": redirect_uri,
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": state,
        "code_challenge": "trendora_twitter_challenge_123",
        "code_challenge_method": "plain"
    }
    base_url = "https://twitter.com/i/oauth2/authorize"
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return jsonify({"success": True, "url": full_url})

@app.route('/auth/twitter/callback', methods=['GET'])
def twitter_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    email = state.split('|')[1] if '|' in state else ''
    
    if code and email:
        try:
            token_url = "https://api.twitter.com/2/oauth2/token"
            payload = {
                "code": code,
                "grant_type": "authorization_code",
                "client_id": TWITTER_CLIENT_ID,
                "redirect_uri": "https://trendoraautomation.my.id/auth/twitter/callback",
                "code_verifier": "trendora_twitter_challenge_123"
            }
            auth_str = f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(token_url, data=data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            req.add_header('Authorization', f'Basic {b64_auth}')
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
                
                sheet = get_gsheet()
                if sheet and access_token:
                    all_vals = sheet.get_all_values()
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            row_idx = idx + 1
                            sheet.update_cell(row_idx, 15, access_token)
                            break
        except Exception as e:
            print("Twitter OAuth Error:", e)

    return """
    <html><body style="background:#0d0a1a;"><h2 style="color:#1d9bf0;text-align:center;margin-top:50px;">Twitter/X Connected!</h2>
    <script>if(window.opener){window.opener.postMessage({type:'OAUTH_SUCCESS', platform:'Twitter'}, '*');window.close();}</script>
    </body></html>
    """

# ==========================================
# TRANSACTIONS LOGIC (MIDTRANS)
# ==========================================
@app.route('/api/create-transaction', methods=['POST'])
def create_transaction():
    data = request.json or {}
    name = data.get('name', 'User')
    email = data.get('email', 'user@example.com').strip().lower()
    plan = data.get('plan', 'Creator')
    price_str = data.get('price', '200000')
    is_upgrading = data.get('isUpgrading', False)

    existing_user = db_get_user(email)
    if existing_user and not is_upgrading:
        return jsonify({"success": False, "message": "Email sudah terdaftar!"})
    try:
        amount = int(re.sub(r'[^\d]', '', price_str))
    except:
        amount = 200000

    order_id = f"ORDER-{uuid.uuid4().hex[:8].upper()}"
    auth_string = base64.b64encode(f"{MIDTRANS_SERVER_KEY}:".encode()).decode()
    payload = {
        "transaction_details": {"order_id": order_id, "gross_amount": amount},
        "customer_details": {"first_name": name, "email": email}
    }

    try:
        req = urllib.request.Request(
            MIDTRANS_API_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={"Authorization": f"Basic {auth_string}", "Content-Type": "application/json"}, 
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if response.status == 201:
                if not existing_user:
                    db_save_user(email, generate_base32_secret(), False, name, "-", "Pending Payment")
                return jsonify({"success": True, "token": res_data.get('token')})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/check-payment', methods=['POST'])
def check_payment():
    return jsonify({"success": True, "isPaid": False})


# ==========================================
# WEBHOOK LISTENER DARI N8N 
# ==========================================
@app.route('/api/n8n-webhook', methods=['GET', 'POST'], strict_slashes=False)
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

    data = request.json or {}
    platform = data.get('platform', 'unknown').lower()
    status = data.get('status', 'RECEIVED')
    details = data.get('details', {})
    
    # -----------------------------------------------------
    # LOGIKA 1: POSTING KE TIKTOK 
    # -----------------------------------------------------
    if platform == 'tiktok' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Diposting otomatis via n8n & TRENDORA! 🚀')
        
        if media_url:
            user_tokens = db_get_tiktok_tokens_by_api_key(api_key)
            access_token = user_tokens.get('access_token')
            
            if access_token:
                temp_file_path = None
                try:
                    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=utf-8"}
                    try:
                        urllib.request.urlopen(urllib.request.Request("https://open.tiktokapis.com/v2/post/publish/creator_info/query/", data=b"{}", headers=headers, method='POST'))
                    except: pass

                    temp_dir = tempfile.gettempdir()
                    temp_file_path = os.path.join(temp_dir, f"tk_{uuid.uuid4().hex[:6]}.mp4")
                    urllib.request.urlretrieve(media_url, temp_file_path)
                    file_size = os.path.getsize(temp_file_path)

                    payload = {
                        "post_info": {"title": caption, "privacy_level": "PUBLIC_TO_EVERYONE", "disable_duet": False, "disable_comment": False, "disable_stitch": False},
                        "source_info": {"source": "FILE_UPLOAD", "video_size": file_size, "chunk_size": file_size, "total_chunk_count": 1}
                    }
                    
                    req_init = urllib.request.Request("https://open.tiktokapis.com/v2/post/publish/video/init/", data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
                    with urllib.request.urlopen(req_init) as response:
                        tiktok_res = json.loads(response.read().decode('utf-8'))
                        upload_url = tiktok_res.get('data', {}).get('upload_url')
                        if upload_url:
                            with open(temp_file_path, 'rb') as f:
                                video_data = f.read()
                            put_headers = {'Content-Type': 'video/mp4', 'Content-Range': f'bytes 0-{file_size-1}/{file_size}'}
                            urllib.request.urlopen(urllib.request.Request(upload_url, data=video_data, headers=put_headers, method='PUT'))
                            status = "PUBLISHED (SUCCESS)"
                            details['upload_status'] = f"Success TikTok Upload ({file_size} bytes)."
                        else:
                            status = "FAILED"
                except Exception as e:
                    details['tiktok_error'] = str(e)
                    status = "FAILED"
                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        try: os.remove(temp_file_path)
                        except: pass
            else:
                details['error'] = "Akun TikTok belum terhubung."
                status = "FAILED"

    # -----------------------------------------------------
    # LOGIKA 2: POSTING KE FACEBOOK PAGE
    # -----------------------------------------------------
    elif platform == 'facebook' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Auto-post by TRENDORA ⚡')
        meta_token = db_get_meta_token_by_api_key(api_key)
        
        if meta_token and media_url:
            try:
                page_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={meta_token}"
                req_page = urllib.request.Request(page_url)
                with urllib.request.urlopen(req_page) as response:
                    page_data = json.loads(response.read().decode('utf-8'))
                    
                if page_data.get('data') and len(page_data['data']) > 0:
                    page_id = page_data['data'][0]['id']
                    page_token = page_data['data'][0]['access_token']
                    page_name = page_data['data'][0].get('name', 'Unknown Page')
                    
                    fb_post_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
                    fb_payload = urllib.parse.urlencode({
                        'file_url': media_url,
                        'description': caption,
                        'access_token': page_token
                    }).encode('utf-8')
                    
                    req_post = urllib.request.Request(fb_post_url, data=fb_payload, method='POST')
                    with urllib.request.urlopen(req_post) as res_post:
                        fb_res = json.loads(res_post.read().decode('utf-8'))
                        status = "PUBLISHED (SUCCESS)"
                        details['fb_status'] = f"Video sukses dipost ke Page: {page_name}"
                        details['fb_video_id'] = fb_res.get('id')
                else:
                    status = "FAILED"
                    details['meta_error'] = "Tidak menemukan satupun Facebook Page di akun ini."
            except Exception as e:
                status = "FAILED"
                details['meta_error'] = f"Graph API Error: {str(e)}"
        else:
            status = "FAILED"
            details['meta_error'] = "Token Facebook tidak valid atau Media URL kosong."

    # -----------------------------------------------------
    # LOGIKA 3: POSTING KE INSTAGRAM REELS 
    # -----------------------------------------------------
    elif platform == 'instagram' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Auto-post Reels by TRENDORA ⚡')
        meta_token = db_get_meta_token_by_api_key(api_key)
        
        if meta_token and media_url:
            try:
                page_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={meta_token}"
                req_page = urllib.request.Request(page_url)
                with urllib.request.urlopen(req_page) as response:
                    page_data = json.loads(response.read().decode('utf-8'))
                    
                if page_data.get('data') and len(page_data['data']) > 0:
                    page_id = page_data['data'][0]['id']
                    ig_info_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={meta_token}"
                    req_ig = urllib.request.Request(ig_info_url)
                    with urllib.request.urlopen(req_ig) as res_ig:
                        ig_data = json.loads(res_ig.read().decode('utf-8'))
                        
                    ig_user_id = ig_data.get('instagram_business_account', {}).get('id')
                    
                    if ig_user_id:
                        ig_container_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
                        ig_payload = urllib.parse.urlencode({
                            'media_type': 'REELS',
                            'video_url': media_url,
                            'caption': caption,
                            'access_token': meta_token
                        }).encode('utf-8')
                        
                        req_container = urllib.request.Request(ig_container_url, data=ig_payload, method='POST')
                        with urllib.request.urlopen(req_container) as res_cont:
                            cont_data = json.loads(res_cont.read().decode('utf-8'))
                            creation_id = cont_data.get('id')
                            
                        time.sleep(5) 
                        
                        ig_publish_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
                        ig_pub_payload = urllib.parse.urlencode({
                            'creation_id': creation_id,
                            'access_token': meta_token
                        }).encode('utf-8')
                        
                        try:
                            req_pub = urllib.request.Request(ig_publish_url, data=ig_pub_payload, method='POST')
                            with urllib.request.urlopen(req_pub) as res_pub:
                                pub_data = json.loads(res_pub.read().decode('utf-8'))
                                status = "PUBLISHED (SUCCESS)"
                                details['ig_status'] = "Sukses upload Instagram Reels!"
                                details['ig_media_id'] = pub_data.get('id')
                        except urllib.error.HTTPError as ep:
                            status = "PENDING / RENDERING"
                            details['ig_status'] = f"Video mendarat di server Meta (ID: {creation_id}). Sedang diproses Instagram..."
                    else:
                        status = "FAILED"
                        details['meta_error'] = "Tidak menemukan Instagram Business Account."
                else:
                    status = "FAILED"
                    details['meta_error'] = "Tidak menemukan FB Page untuk mengekstrak IG Account."
            except Exception as e:
                status = "FAILED"
                details['meta_error'] = f"Graph API Error: {str(e)}"
        else:
            status = "FAILED"
            details['meta_error'] = "Token Meta tidak valid."
            
    # -----------------------------------------------------
    # LOGIKA 4: POSTING KE LINKEDIN (TEXT & VIDEO)
    # -----------------------------------------------------
    elif platform == 'linkedin' and isinstance(details, dict):
        caption = details.get('caption', 'Posting via n8n & TRENDORA')
        media_url = details.get('media_url')
        linkedin_token = db_get_linkedin_token_by_api_key(api_key)
        
        if linkedin_token:
            temp_file_path = None
            try:
                # 1. Dapatkan URN Profil User
                profile_url = "https://api.linkedin.com/v2/userinfo"
                req_profile = urllib.request.Request(profile_url, headers={"Authorization": f"Bearer {linkedin_token}"})
                with urllib.request.urlopen(req_profile) as res_profile:
                    profile_data = json.loads(res_profile.read().decode('utf-8'))
                    sub_urn = profile_data.get('sub')
                
                if sub_urn:
                    author_urn = f"urn:li:person:{sub_urn}"
                    
                    if media_url:
                        # --- UNGGAH DENGAN VIDEO ---
                        # A. Download file video temporer
                        temp_dir = tempfile.gettempdir()
                        temp_file_path = os.path.join(temp_dir, f"li_{uuid.uuid4().hex[:6]}.mp4")
                        urllib.request.urlretrieve(media_url, temp_file_path)
                        
                        # B. Registrasikan Aset Video Upload
                        reg_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
                        reg_payload = {
                            "registerUploadRequest": {
                                "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                                "owner": author_urn,
                                "serviceRelationships": [
                                    {
                                        "relationshipType": "OWNER",
                                        "identifier": "urn:li:userGeneratedContent"
                                    }
                                ]
                            }
                        }
                        req_reg = urllib.request.Request(
                            reg_url, 
                            data=json.dumps(reg_payload).encode('utf-8'),
                            headers={
                                "Authorization": f"Bearer {linkedin_token}",
                                "Content-Type": "application/json"
                            },
                            method='POST'
                        )
                        
                        with urllib.request.urlopen(req_reg) as res_reg:
                            reg_data = json.loads(res_reg.read().decode('utf-8'))
                            value = reg_data.get('value', {})
                            asset_urn = value.get('asset')
                            upload_url = value.get('uploadMechanism', {}).get('com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest', {}).get('uploadUrl')
                        
                        if upload_url and asset_urn:
                            # C. Upload Binary Data Video
                            with open(temp_file_path, 'rb') as f:
                                video_data = f.read()
                                
                            req_up = urllib.request.Request(
                                upload_url,
                                data=video_data,
                                headers={
                                    "Authorization": f"Bearer {linkedin_token}",
                                    "Content-Type": "application/octet-stream"
                                },
                                method='PUT'
                            )
                            urllib.request.urlopen(req_up)
                            
                            # D. Publish UGC Video Post
                            post_url = "https://api.linkedin.com/v2/ugcPosts"
                            post_payload = {
                                "author": author_urn,
                                "lifecycleState": "PUBLISHED",
                                "specificContent": {
                                    "com.linkedin.ugc.ShareContent": {
                                        "shareCommentary": {"text": caption},
                                        "shareMediaCategory": "VIDEO",
                                        "media": [
                                            {
                                                "status": "READY",
                                                "description": {"text": caption[:200]},
                                                "media": asset_urn,
                                                "title": {"text": "Video"}
                                            }
                                        ]
                                    }
                                },
                                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
                            }
                        else:
                            raise Exception("Gagal mendapatkan URL upload dari LinkedIn API.")
                    else:
                        # --- POSTING TEKS SAJA ---
                        post_url = "https://api.linkedin.com/v2/ugcPosts"
                        post_payload = {
                            "author": author_urn,
                            "lifecycleState": "PUBLISHED",
                            "specificContent": {
                                "com.linkedin.ugc.ShareContent": {
                                    "shareCommentary": {"text": caption},
                                    "shareMediaCategory": "NONE"
                                }
                            },
                            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
                        }
                    
                    req_post = urllib.request.Request(
                        post_url, 
                        data=json.dumps(post_payload).encode('utf-8'),
                        headers={
                            "Authorization": f"Bearer {linkedin_token}",
                            "Content-Type": "application/json",
                            "X-Restli-Protocol-Version": "2.0.0"
                        },
                        method='POST'
                    )
                    
                    with urllib.request.urlopen(req_post) as res_post:
                        status = "PUBLISHED (SUCCESS)"
                        details['linkedin_status'] = "Sukses upload video ke LinkedIn!"
                else:
                    status = "FAILED"
                    details['linkedin_error'] = "Gagal mengambil ID Akun (URN)."
            except Exception as e:
                status = "FAILED"
                details['linkedin_error'] = f"LinkedIn API Error: {str(e)}"
            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    try: os.remove(temp_file_path)
                    except: pass
        else:
            status = "FAILED"
            details['linkedin_error'] = "Token LinkedIn tidak valid atau belum terhubung."

    # -----------------------------------------------------
    # LOGIKA 5: POSTING KE YOUTUBE (SHORTS/VIDEO)
    # -----------------------------------------------------
    elif platform == 'youtube' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Auto-post by TRENDORA')
        
        # Ambil Token YouTube dari GSheet
        yt_tokens = {}
        sheet = get_gsheet()
        if sheet:
            try:
                all_values = sheet.get_all_values()
                for idx, row in enumerate(all_values):
                    if idx == 0: continue
                    if len(row) >= 5 and row[4].strip() == api_key:
                        yt_tokens = {
                            'access_token': row[11] if len(row) >= 12 else None, # Index 11 = Access Token
                            'refresh_token': row[12] if len(row) >= 13 else None # Index 12 = Refresh Token
                        }
            except Exception as e:
                print(f"GSheet Get YT Tokens Error: {e}")

        access_token = yt_tokens.get('access_token')
        refresh_token = yt_tokens.get('refresh_token')
        
        if access_token:
            def attempt_youtube_upload(token):
                # 1. Download Video Sementara
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, f"yt_{uuid.uuid4().hex[:6]}.mp4")
                urllib.request.urlretrieve(media_url, temp_file_path)
                file_size = os.path.getsize(temp_file_path)
                
                try:
                    # 2. Inisiasi Upload API YouTube (Resumable)
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json; charset=UTF-8",
                        "X-Upload-Content-Length": str(file_size),
                        "X-Upload-Content-Type": "video/mp4"
                    }
                    body = {
                        "snippet": {
                            "title": caption[:100], # YouTube Title max 100 char
                            "description": caption,
                            "categoryId": "22" # Kategori People & Blogs
                        },
                        "status": {
                            "privacyStatus": "public",
                            "selfDeclaredMadeForKids": False
                        }
                    }
                    req_init = urllib.request.Request(
                        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                        data=json.dumps(body).encode('utf-8'), headers=headers, method='POST'
                    )
                    
                    with urllib.request.urlopen(req_init) as response:
                        upload_url = response.headers.get('Location')
                        
                    if not upload_url:
                        raise Exception("Gagal mendapatkan Upload URL dari YouTube")
                        
                    # 3. Upload File Video Binary
                    with open(temp_file_path, 'rb') as f:
                        video_data = f.read()
                        
                    put_headers = {"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"}
                    req_upload = urllib.request.Request(upload_url, data=video_data, headers=put_headers, method='PUT')
                    with urllib.request.urlopen(req_upload) as res_upload:
                        yt_res = json.loads(res_upload.read().decode('utf-8'))
                        return yt_res
                finally:
                    # Hapus file sampah video biar server Vercel gak penuh
                    if os.path.exists(temp_file_path):
                        try: os.remove(temp_file_path)
                        except: pass
                
            try:
                # 1. PERCOBAAN PERTAMA
                yt_result = attempt_youtube_upload(access_token)
                status = "PUBLISHED (SUCCESS)"
                details['yt_status'] = "Sukses Upload ke YouTube!"
                details['youtube_video_id'] = yt_result.get('id')
            except urllib.error.HTTPError as e:
                # 2. AUTO REFRESH JIKA KENA ERROR 401
                if e.code == 401 and refresh_token:
                    try:
                        token_url = "https://oauth2.googleapis.com/token"
                        payload = {
                            "client_id": os.environ.get("YOUTUBE_CLIENT_ID", ""),
                            "client_secret": os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token"
                        }
                        data = urllib.parse.urlencode(payload).encode('utf-8')
                        req_refresh = urllib.request.Request(token_url, data=data, method='POST')
                        
                        with urllib.request.urlopen(req_refresh) as res_refresh:
                            ref_data = json.loads(res_refresh.read().decode('utf-8'))
                            new_access_token = ref_data.get('access_token')
                            
                            if new_access_token:
                                # Update token baru ke Google Sheets
                                if sheet:
                                    all_vals = sheet.get_all_values()
                                    for idx, row in enumerate(all_vals):
                                        if idx == 0: continue
                                        if len(row) >= 5 and row[4].strip() == api_key:
                                            sheet.update_cell(idx + 1, 12, new_access_token)
                                            break
                                
                                # 3. COBA UPLOAD ULANG DENGAN TOKEN BARU
                                yt_result_retry = attempt_youtube_upload(new_access_token)
                                status = "PUBLISHED (SUCCESS)"
                                details['yt_status'] = "Sukses dengan Auto-Refresh Token"
                                details['youtube_video_id'] = yt_result_retry.get('id')
                            else:
                                raise Exception("Gagal mendapat access_token baru.")
                    except Exception as refresh_err:
                        status = "FAILED"
                        details['yt_error'] = f"YouTube 401 & Auto-Refresh Gagal: {str(refresh_err)}"
                else:
                    status = "FAILED"
                    details['yt_error'] = f"YouTube HTTP Error: {str(e)}"
            except Exception as e:
                status = "FAILED"
                details['yt_error'] = f"YouTube Process Error: {str(e)}"
        else:
            status = "FAILED"
            details['yt_error'] = "Token YouTube tidak valid atau belum login."
            
    # -----------------------------------------------------
    # LOGIKA 6: POSTING KE THREADS
    # -----------------------------------------------------
    elif platform == 'threads' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Auto-post Threads by TRENDORA ⚡')
        threads_token = db_get_threads_token_by_api_key(api_key)
        
        if threads_token and media_url:
            try:
                me_url = f"https://graph.threads.net/v1.0/me?access_token={threads_token}"
                req_me = urllib.request.Request(me_url)
                with urllib.request.urlopen(req_me) as res_me:
                    me_data = json.loads(res_me.read().decode('utf-8'))
                    threads_user_id = me_data.get('id')
                    
                if threads_user_id:
                    container_url = f"https://graph.threads.net/v1.0/{threads_user_id}/threads"
                    payload = urllib.parse.urlencode({
                        'media_type': 'VIDEO',
                        'video_url': media_url,
                        'text': caption,
                        'access_token': threads_token
                    }).encode('utf-8')
                    
                    req_cont = urllib.request.Request(container_url, data=payload, method='POST')
                    with urllib.request.urlopen(req_cont) as res_cont:
                        cont_data = json.loads(res_cont.read().decode('utf-8'))
                        creation_id = cont_data.get('id')
                        
                    time.sleep(5)
                    
                    publish_url = f"https://graph.threads.net/v1.0/{threads_user_id}/threads_publish"
                    pub_payload = urllib.parse.urlencode({
                        'creation_id': creation_id,
                        'access_token': threads_token
                    }).encode('utf-8')
                    
                    try:
                        req_pub = urllib.request.Request(publish_url, data=pub_payload, method='POST')
                        with urllib.request.urlopen(req_pub) as res_pub:
                            pub_data = json.loads(res_pub.read().decode('utf-8'))
                            status = "PUBLISHED (SUCCESS)"
                            details['threads_status'] = "Sukses upload ke Threads!"
                            details['threads_media_id'] = pub_data.get('id')
                    except urllib.error.HTTPError as ep:
                        status = "PENDING / RENDERING"
                        details['threads_status'] = f"Video mendarat di Meta (ID: {creation_id}). Sedang diproses Threads..."
                else:
                    status = "FAILED"
                    details['threads_error'] = "Gagal mendapatkan ID Threads."
            except Exception as e:
                status = "FAILED"
                details['threads_error'] = f"Threads API Error: {str(e)}"
        else:
            status = "FAILED"
            details['threads_error'] = "Token Threads tidak valid atau Media URL kosong."

    # -----------------------------------------------------
    # LOGIKA 7: POSTING KE TWITTER (X)
    # -----------------------------------------------------
    elif platform == 'twitter' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Auto-post by TRENDORA')
        twitter_token = db_get_twitter_token_by_api_key(api_key)
        
        if twitter_token:
            try:
                tweet_text = f"{caption}\n\n{media_url}" if media_url else caption
                
                tweet_url = "https://api.twitter.com/2/tweets"
                payload = {"text": tweet_text}
                
                req_tweet = urllib.request.Request(
                    tweet_url, 
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        "Authorization": f"Bearer {twitter_token}",
                        "Content-Type": "application/json"
                    },
                    method='POST'
                )
                
                with urllib.request.urlopen(req_tweet) as res_tweet:
                    tweet_data = json.loads(res_tweet.read().decode('utf-8'))
                    status = "PUBLISHED (SUCCESS)"
                    details['twitter_status'] = "Sukses post Tweet!"
                    details['tweet_id'] = tweet_data.get('data', {}).get('id')
            except Exception as e:
                status = "FAILED"
                details['twitter_error'] = f"Twitter API Error: {str(e)}"
        else:
            status = "FAILED"
            details['twitter_error'] = "Token Twitter tidak valid."


    # -----------------------------------------------------
    # LOGGING KE DATABASE (TER-ISOLASI PER USER)
    # -----------------------------------------------------
    media_url_val = ""
    caption_val = ""
    hashtag_val = ""
    
    if isinstance(details, dict):
        # Gunakan .pop() untuk mencabut data dari 'details' agar pindah ke kolom baru
        media_url_val = details.pop('media_url', '')
        caption_val = details.pop('caption', '')
        hashtag_val = details.pop('hashtag', '')
        details_str = json.dumps(details)
    else:
        details_str = str(details)
        
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
    
    # SUSUNAN DATA VERTICAL (Sesuaikan dengan urutan Kolom Google Sheets Lu)
    row_data = [
        timestamp,       # Kolom A
        log_id,          # Kolom B
        api_key,         # Kolom C
        platform,        # Kolom D
        status,          # Kolom E
        details_str,     # Kolom F
        "",              # Kolom G (Keterangan - sengaja dikosongkan)
        media_url_val,   # Kolom H (Media URL)
        caption_val,     # Kolom I (Caption)
        hashtag_val      # Kolom J (Hashtag)
    ]
    
    sheet = get_logs_sheet()
    if sheet:
        try:
            # Hitung baris kosong terakhir berdasarkan Kolom A
            col_a = sheet.col_values(1)
            next_row = len(col_a) + 1
            
            # Tembak data spesifik ke range A sampai J di baris kosong tersebut
            cell_range = f"A{next_row}:J{next_row}"
            sheet.update(values=[row_data], range_name=cell_range)
            
            return jsonify({"success": True, "message": "Processed & Logged", "log_id": log_id})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    else:
        if 'logs' not in user_2fa_store: user_2fa_store['logs'] = []
        user_2fa_store['logs'].append({
            "Timestamp": timestamp, 
            "LogID": log_id, 
            "APIKey": api_key, 
            "Platform": platform, 
            "Status": status, 
            "Details": details_str,
            "Keterangan": "",
            "MediaURL": media_url_val,
            "Caption": caption_val,
            "Hashtag": hashtag_val
        })
        return jsonify({"success": True, "log_id": log_id})

@app.route('/api/get-logs', methods=['POST', 'GET'])
def get_logs():
    api_key = request.headers.get('X-API-Key', '').strip()
    if not api_key:
        data = request.json or {}
        api_key = data.get('api_key', '').strip()
        
    logs = []
    sheet = get_logs_sheet()
    
    if sheet:
        try:
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                for row in all_values[1:]:
                    if len(row) >= 3:
                        row_api_key = str(row[2]).strip()
                        
                        if api_key and row_api_key != api_key:
                            continue
                            
                        log_entry = {
                            "Timestamp": str(row[0]).strip() if len(row) > 0 else "-", 
                            "LogID": str(row[1]).strip() if len(row) > 1 else "-",
                            "Platform": str(row[3]).strip() if len(row) > 3 else "-", 
                            "Status": str(row[4]).strip() if len(row) > 4 else "-",
                            "Details": str(row[5]).strip() if len(row) > 5 else "-"
                        }
                        logs.append(log_entry)
            
            logs.reverse()
            return jsonify({"success": True, "logs": logs[:50]})
        except Exception as e: 
            print(f"Get logs error: {e}")
            return jsonify({"success": False, "message": str(e)})
    
    if 'logs' in user_2fa_store:
        all_mem_logs = user_2fa_store['logs']
        if api_key:
            logs = [log for log in all_mem_logs if log.get('APIKey') == api_key]
        else:
            logs = all_mem_logs
        logs.reverse()
        return jsonify({"success": True, "logs": logs[:50]})
        
    return jsonify({"success": True, "logs": []})

if __name__ == '__main__':
    app.run(debug=True)