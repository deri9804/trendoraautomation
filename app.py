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

# KONFIGURASI TIKTOK DEVELOPER (Sekarang ambil dari Vercel Env)
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET")

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
    """Koneksi ke Google Sheets khusus tab 'Logs'. Sangat kebal error!"""
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
        
        # Cari berbagai kemungkinan nama tab yang mungkin diketik user
        possible_names = ["Logs", "logs", "Log", "log", "LOGS", "Logs "]
        sheet = None
        for name in possible_names:
            try:
                sheet = doc.worksheet(name)
                break
            except:
                continue
                
        # SUPER BULLETPROOF: Kalau beneran gak ketemu, BIKININ OTOMATIS!
        if not sheet:
            sheet = doc.add_worksheet(title="Logs", rows="1000", cols="10")
            sheet.append_row(["Timestamp", "LogID", "APIKey", "Platform", "Status", "Details"])
            
        return sheet
    except Exception as e:
        print(f"GSheets Logs Connection Error: {e}")
        return None

def db_get_user(email):
    """Ambil data user dari Google Sheets (scan dari BAWAH agar selalu dapat yg terbaru jika duplikat)."""
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                # Loop dari bawah ke atas
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
                            'row_idx': idx + 1  
                        }
            return None
        except Exception as e:
            print(f"GSheet Read Error: {e}")
            return None
            
    # Fallback memory
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
    """Fungsi krusial untuk mengambil Access Token TikTok saat n8n mengirim webhook."""
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            # Mencari baris yang API Key-nya cocok (Kolom ke-5 / index 4)
            for idx, row in enumerate(all_values):
                if idx == 0: continue # Skip header
                if len(row) >= 5 and row[4].strip() == api_key:
                    return {
                        'access_token': row[6] if len(row) >= 7 else None,
                        'open_id': row[7] if len(row) >= 8 else None
                    }
        except Exception as e:
            print(f"GSheet Get Tokens Error: {e}")
    return {}

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

@app.route('/tos')
def tos_page(): return render_template('tos.html')

@app.route('/privacy')
def privacy_page(): return render_template('privacy.html')

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
        
        # CEK KONEKSI TIKTOK DARI DATABASE (Agar UI Dashboard Update)
        connected_platforms = []
        if user_data.get('tiktok_connected'):
            connected_platforms.append('TikTok')
        
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
    """Route rahasia buat sinkronisasi otomatis status frontend dan database."""
    email = request.json.get('email', '').strip().lower()
    if not email: return jsonify({"success": False})
    
    user_data = db_get_user(email)
    if not user_data: return jsonify({"success": False})
    
    connected_platforms = []
    if user_data.get('tiktok_connected'):
        connected_platforms.append('TikTok')
        
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
# ROUTE UNTUK VERIFIKASI DOMAIN TIKTOK
# ==========================================
@app.route('/tiktok-verify.txt') # Nanti nama file ini bisa disesuaikan sama yang dikasih TikTok
def tiktok_verify():
    # Kalau TikTok minta verifikasi domain, lu masukin kode unik dari mereka ke sini
    tiktok_verification_code = "tiktok-verification-code-masukin-nanti-disini"
    return tiktok_verification_code, 200, {'Content-Type': 'text/plain'}

# ==========================================
# REAL TIKTOK OAUTH & DIRECT POST INTEGRATION
# ==========================================
@app.route('/api/tiktok-auth-url', methods=['GET'])
def get_tiktok_auth_url():
    """Route untuk menggenerate URL Login TikTok asli. Membawa email user di parameter 'state'."""
    email = request.args.get('email', '').strip()
    redirect_uri = "https://trendoraautomation.my.id/auth/tiktok/callback"
    
    # Kita titip email user di parameter state biar pas callback kita tau ini akun siapa
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
    """Menerima kode dari TikTok, lalu menukarnya dengan Access Token secara real."""
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
                    # Cari dari bawah biar selalu nemu row terbaru
                    for idx in range(len(all_vals)-1, 0, -1):
                        row = all_vals[idx]
                        if len(row) > 0 and str(row[0]).strip().lower() == email.lower():
                            row_idx = idx + 1
                            sheet.update_cell(row_idx, 7, access_token)
                            sheet.update_cell(row_idx, 8, open_id)
                            sheet.update_cell(row_idx, 9, refresh_token)
                            break
                            
        except Exception as e:
            print("TikTok OAuth Error Detail:", e)

    return """
    <html>
    <head><title>TikTok Connected</title></head>
    <body style="background-color: #0d0a1a; color: #fff; font-family: sans-serif; text-align: center; padding-top: 50px;">
        <h2 style="color: #34d399;">TikTok Successfully Authorized!</h2>
        <p style="color: #9ca3af;">Please wait, saving your token...</p>
        <script>
            if (window.opener) {
                window.opener.postMessage({type: 'OAUTH_SUCCESS', platform: 'TikTok'}, '*');
                window.close();
            }
        </script>
    </body>
    </html>
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
# WEBHOOK LISTENER DARI N8N (THE MASTERPIECE)
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

    data = request.json or {}
    platform = data.get('platform', 'unknown').lower()
    status = data.get('status', 'RECEIVED')
    details = data.get('details', {})
    
    if not api_key:
        return jsonify({"success": False, "message": "API Key is required in Header"}), 400
    
    # 💥 METODE TERBARU: WEB NYEDOT VIDEO & NYEBUL LANGSUNG KE TIKTOK (FILE_UPLOAD) 💥
    if platform == 'tiktok' and isinstance(details, dict):
        media_url = details.get('media_url')
        caption = details.get('caption', 'Diposting otomatis via n8n & TRENDORA! 🚀')
        
        if media_url:
            user_tokens = db_get_tiktok_tokens_by_api_key(api_key)
            access_token = user_tokens.get('access_token')
            
            if access_token:
                temp_file_path = None
                try:
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json; charset=utf-8"
                    }

                    # LANGKAH 1: KETOK PINTU (Query Creator Info)
                    query_url = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
                    req_query = urllib.request.Request(query_url, data=b"{}", headers=headers, method='POST')
                    try:
                        urllib.request.urlopen(req_query)
                    except Exception as eq:
                        pass # Abaikan kalau error, tetap lanjut

                    # LANGKAH 2: WEB KITA DOWNLOAD/NYEDOT VIDEO DARI GOOGLE STORAGE
                    temp_dir = tempfile.gettempdir()
                    temp_file_path = os.path.join(temp_dir, f"tiktok_vid_{uuid.uuid4().hex[:6]}.mp4")
                    urllib.request.urlretrieve(media_url, temp_file_path)
                    file_size = os.path.getsize(temp_file_path)

                    # LANGKAH 3: INIT UPLOAD KE TIKTOK (MINTA UPLOAD URL)
                    tiktok_api_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
                    payload = {
                        "post_info": {
                            "title": caption,
                            "privacy_level": "SELF_ONLY", # Private Mode
                            "disable_duet": False,
                            "disable_comment": False,
                            "disable_stitch": False
                        },
                        "source_info": {
                            "source": "FILE_UPLOAD", # INI KUNCI UTAMANYA!
                            "video_size": file_size,
                            "chunk_size": file_size,
                            "total_chunk_count": 1
                        }
                    }
                    
                    req_init = urllib.request.Request(
                        tiktok_api_url, 
                        data=json.dumps(payload).encode('utf-8'), 
                        headers=headers, 
                        method='POST'
                    )
                    
                    with urllib.request.urlopen(req_init) as response:
                        tiktok_res = json.loads(response.read().decode('utf-8'))
                        details['tiktok_init_response'] = tiktok_res
                        
                        upload_url = tiktok_res.get('data', {}).get('upload_url')
                        publish_id = tiktok_res.get('data', {}).get('publish_id')
                        
                        if upload_url and publish_id:
                            # LANGKAH 4: WEB KITA UPLOAD FISIK VIDEONYA KE SERVER TIKTOK
                            with open(temp_file_path, 'rb') as f:
                                video_data = f.read()
                                
                            put_headers = {
                                'Content-Type': 'video/mp4',
                                'Content-Range': f'bytes 0-{file_size-1}/{file_size}'
                            }
                            
                            req_upload = urllib.request.Request(upload_url, data=video_data, headers=put_headers, method='PUT')
                            urllib.request.urlopen(req_upload)
                            
                            status = "PUBLISHED (SUCCESS)"
                            details['upload_status'] = f"Success! Web Vercel uploaded {file_size} bytes to TikTok."
                        else:
                            status = "FAILED (NO UPLOAD URL)"
                        
                except urllib.error.HTTPError as e:
                    try:
                        error_body = e.read().decode('utf-8')
                        details['tiktok_real_error'] = f"HTTP {e.code}: {error_body}"
                    except:
                        details['tiktok_real_error'] = f"HTTP {e.code}: Forbidden"
                    status = "FAILED"
                except Exception as e:
                    details['tiktok_real_error'] = str(e)
                    status = "FAILED"
                finally:
                    # LANGKAH 5: BERSIH-BERSIH RAM VERCEL
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                        except:
                            pass
            else:
                details['tiktok_real_error'] = "User belum menghubungkan akun TikTok (Token tidak ada)."
                status = "FAILED"

    if isinstance(details, dict):
        details_str = json.dumps(details)
    else:
        details_str = str(details)
        
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
    
    sheet = get_logs_sheet()
    if sheet:
        try:
            sheet.append_row([timestamp, log_id, api_key, platform, status, details_str])
            return jsonify({"success": True, "message": "Processed & Logged", "log_id": log_id})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    else:
        if 'logs' not in user_2fa_store: user_2fa_store['logs'] = []
        user_2fa_store['logs'].append({"Timestamp": timestamp, "LogID": log_id, "APIKey": api_key, "Platform": platform, "Status": status, "Details": details_str})
        return jsonify({"success": True, "log_id": log_id})

# ==========================================
# WEBHOOK RESMI DARI TIKTOK (ADS / LEAD GEN)
# ==========================================
@app.route('/api/tiktok-webhook', methods=['GET', 'POST'], strict_slashes=False)
def tiktok_webhook():
    """Menerima Webhook resmi dari server TikTok (misal untuk Ads, Lead Gen, atau Event Subscription)."""
    
    # TikTok kadang mengirim challenge via GET request untuk memverifikasi kepemilikan URL
    if request.method == 'GET':
        challenge = request.args.get('challenge')
        if challenge:
            # Wajib membalas challenge agar TikTok memvalidasi URL webhook
            return jsonify({"challenge": challenge}), 200
        return jsonify({"success": True, "message": "🟢 Endpoint Webhook TikTok Aktif dan Siap Menerima Data!"}), 200

    # Kalau POST, berarti TikTok sedang mengirim payload data beneran (iklan/event)
    data = request.json or {}
    
    # Bikin ID Log khusus buat ngebedain dari n8n
    log_id = f"TK-ADS-{uuid.uuid4().hex[:6].upper()}"
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    details_str = json.dumps(data)
    
    # Simpan ke Google Sheets (Tab Logs)
    sheet = get_logs_sheet()
    if sheet:
        try:
            sheet.append_row([timestamp, log_id, "TIKTOK_SYSTEM", "tiktok_ads", "RECEIVED", details_str])
        except Exception as e:
            pass
            
    return jsonify({"message": "OK", "success": True}), 200

@app.route('/api/get-logs', methods=['POST'])
def get_logs():
    api_key = request.headers.get('X-API-Key', '').strip()
    
    # Toleransi kalau Header diblokir Vercel, kita ambil dari Body JSON
    if not api_key: 
        data = request.get_json(silent=True) or {}
        api_key = data.get('api_key', '').strip()
        
    if not api_key: return jsonify({"success": False, "message": "API Key is required"})
        
    logs = []
    sheet = get_logs_sheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                # Skip header, baca berdasarkan urutan index
                for row in all_values[1:]:
                    # BIKIN KEBAL: Google Sheet kadang motong kolom kosong di ujung, jadi kita cuma butuh minimal 3 kolom (Timestamp, LogID, API Key)
                    if len(row) >= 3:
                        row_api = str(row[2]).strip() # Kolom ke-3 adalah API Key
                        if row_api == api_key:
                            logs.append({
                                "Timestamp": str(row[0]) if len(row) > 0 else "-", 
                                "LogID": str(row[1]) if len(row) > 1 else "-",
                                "Platform": str(row[3]) if len(row) > 3 else "-", 
                                "Status": str(row[4]) if len(row) > 4 else "-",
                                "Details": str(row[5]) if len(row) > 5 else "-"
                            })
            logs.reverse()
            return jsonify({"success": True, "logs": logs})
        except Exception as e: 
            print(f"Get logs error: {e}")
    
    # Fallback memory jika google sheet error
    if 'logs' in user_2fa_store:
        for row in user_2fa_store['logs']:
            if str(row.get('APIKey')).strip() == api_key: logs.append(row)
        logs.reverse()
    return jsonify({"success": True, "logs": logs})

if __name__ == '__main__':
    app.run(debug=True)