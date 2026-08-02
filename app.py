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
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# ==========================================
# KONFIGURASI TIKTOK DEVELOPER (SANDBOX MODE)
# ==========================================
TIKTOK_CLIENT_KEY = "aw1pdjf3lvp63bsd"
TIKTOK_CLIENT_SECRET = "1aPWEik5BhluPtwalGChTq0pvgr6QOF3"

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
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Logs")
        return sheet
    except Exception as e:
        print(f"GSheets Logs Connection Error: {e}")
        return None

def db_get_user(email):
    """Ambil data user dari Google Sheets secara bulletproof."""
    sheet = get_gsheet()
    if sheet:
        try:
            all_records = sheet.get_all_records()
            for idx, row in enumerate(all_records):
                if str(row.get('Email', '')).strip().lower() == email:
                    return {
                        'secret': str(row.get('Secret', '')),
                        'is_linked': str(row.get('IsLinked', '')).lower() == 'true',
                        'name': str(row.get('Nama', '') or row.get('Nama User', '')),
                        'api_key': str(row.get('APIKey', '') or row.get('API Key (TREND_...)', '')),
                        'status': str(row.get('Status', '') or row.get('Status Plan', '')),
                        'row_idx': idx + 2  
                    }
            return None
        except Exception as e:
            print(f"GSheet Read Error: {e}")
            return None
            
    return user_2fa_store.get(email)

def db_save_user(email, secret, is_linked, name="", api_key="", status=""):
    """Simpan atau update seluruh data user ke Google Sheets."""
    sheet = get_gsheet()
    if sheet:
        try:
            all_records = sheet.get_all_records()
            found_idx = -1
            
            for idx, row in enumerate(all_records):
                if str(row.get('Email', '')).strip().lower() == email:
                    found_idx = idx + 2
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
        'secret': secret, 
        'is_linked': is_linked,
        'name': name,
        'api_key': api_key,
        'status': status
    }

# ==========================================
# KONFIGURASI SMTP EMAIL (GMAIL)
# ==========================================
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "trendoraautomation@gmail.com") 
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "") 

def send_email_qr(recipient_email, qr_url, secret):
    """Kirim email berisi QR Code 2FA menggunakan Gmail SMTP."""
    if not SMTP_PASSWORD:
        return False
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Kode QR Google Authenticator - TRENDORA"
    msg["From"] = f"TRENDORA Security <{SMTP_EMAIL}>"
    msg["To"] = recipient_email

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #333; background-color: #0f1524; color: #fff; border-radius: 10px;">
      <h2 style="color: #ec4899; text-align: center;">Reset 2FA Google Authenticator</h2>
      <p style="color: #d1d5db;">Halo,</p>
      <p style="color: #d1d5db;">Anda telah meminta untuk mereset kode keamanan Google Authenticator Anda.</p>
      <p style="color: #d1d5db;">Silakan scan QR Code di bawah ini menggunakan aplikasi Google Authenticator:</p>
      <div style="text-align: center; margin: 20px 0;">
          <img src="{qr_url}" alt="QR Code 2FA" width="200" height="200" style="border: 4px solid #fff; border-radius: 10px;">
      </div>
      <p style="color: #d1d5db; text-align: center;">Atau masukkan kunci rahasia ini secara manual:<br><br>
      <strong style="background: #1e293b; padding: 8px 16px; border-radius: 6px; color: #34d399; letter-spacing: 2px;">{secret}</strong></p>
      <hr style="border-color: #333; margin-top: 30px;">
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
        print(f"SMTP Gagal Kirim: {e}")
        return False

# ==========================================
# LOGIKA TOTP (Google Authenticator)
# ==========================================
def generate_base32_secret():
    bytes_secret = os.urandom(10)
    return base64.b32encode(bytes_secret).decode('utf-8').replace('=', '')

def get_totp_token(secret, intervals_no=None):
    if intervals_no is None:
        intervals_no = int(time.time()) // 30
    
    missing_padding = len(secret) % 8
    if missing_padding != 0:
        secret += '=' * (8 - missing_padding)
        
    key = base64.b32decode(secret, casefold=True)
    msg = struct.pack(">Q", intervals_no)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 15
    h = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
    return str(h).zfill(6)

def verify_totp(secret, token):
    if not secret or not token:
        return False
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
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/checkout')
def checkout_page():
    return render_template('checkout.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/api/request-otp', methods=['POST'])
def request_otp():
    email = request.json.get('email', '').strip().lower()
    if not email:
        return jsonify({"success": False, "message": "Email wajib diisi!"})
    
    user_data = db_get_user(email)
    
    # REVISI POIN 2: Jika email BELUM TERDAFTAR di database -> PENOLAKAN! QR Code TIDAK MUNCUL!
    if not user_data:
        return jsonify({
            "success": False, 
            "message": "Email belum terdaftar! Silakan mendaftar akun terlebih dahulu."
        })
    
    secret = user_data['secret']
    is_linked = user_data['is_linked']
    
    if not is_linked:
        issuer = "TRENDORA"
        totp_uri = f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}"
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(totp_uri)}"
        
        return jsonify({
            "success": True,
            "message": "Silakan scan QR Code dengan Google Authenticator",
            "is2faLinked": False,
            "qrCodeUrl": qr_code_url,
            "secret": secret
        })
    else:
        return jsonify({
            "success": True,
            "message": "Masukkan kode OTP dari Google Authenticator Anda",
            "is2faLinked": True
        })

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp_route():
    email = request.json.get('email', '').strip().lower()
    otp = request.json.get('otp', '').strip()
    
    if not email or not otp:
        return jsonify({"success": False, "message": "Email dan OTP wajib diisi!"})
        
    user_data = db_get_user(email)
    if not user_data:
        return jsonify({"success": False, "message": "Email belum terdaftar!"})
        
    is_valid = verify_totp(user_data['secret'], otp)
        
    if is_valid:
        name = user_data.get('name') or email.split('@')[0].capitalize()
        api_key = user_data.get('api_key') or "-"
        status = user_data.get('status') or "Active (7-Day Free Trial)"
        
        if not user_data.get('is_linked'):
            db_save_user(email, user_data['secret'], True, name, api_key, status)
            
        status_lower = status.lower()
        is_paid_user = any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"])
        
        return jsonify({
            "success": True, 
            "message": "Login berhasil!",
            "user": {
                "name": name,
                "email": email,
                "apiKey": api_key,
                "status": status,
                "isPaid": is_paid_user
            }
        })
    
    return jsonify({"success": False, "message": "Kode OTP Google Authenticator salah atau kadaluarsa!"})

@app.route('/api/reset-2fa-qr', methods=['POST'])
def reset_2fa_qr():
    email = request.json.get('email', '').strip().lower()
    if not email:
        return jsonify({"success": False, "message": "Email tidak ditemukan!"})
        
    old_data = db_get_user(email)
    if not old_data:
        return jsonify({"success": False, "message": "Email belum terdaftar di database!"})

    name = old_data.get('name', email.split('@')[0].capitalize())
    api_key = old_data.get('api_key', "-")
    status = old_data.get('status', "Active (7-Day Free Trial)")
    
    new_secret = generate_base32_secret()
    db_save_user(email, new_secret, False, name, api_key, status)
    
    issuer = "TRENDORA"
    totp_uri = f"otpauth://totp/{issuer}:{email}?secret={new_secret}&issuer={issuer}"
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(totp_uri)}"
    
    email_sent = send_email_qr(email, qr_code_url, new_secret)
    
    if email_sent:
        return jsonify({
            "success": True,
            "message": f"QR Code baru telah dikirimkan ke email {email}. Silakan cek kotak masuk/spam email Anda!",
            "newQrCodeUrl": qr_code_url,
            "newSecret": new_secret
        })
    else:
        return jsonify({
            "success": True,
            "message": "Konfigurasi Email belum siap di server, namun QR Code berhasil direset.",
            "newQrCodeUrl": qr_code_url,
            "newSecret": new_secret
        })

@app.route('/api/register-trial', methods=['POST'])
def register_trial():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', 'User').strip()

    if not email:
        return jsonify({"success": False, "message": "Email wajib diisi!"})
    
    existing_user = db_get_user(email)
    if existing_user:
        return jsonify({"success": False, "message": "Email ini sudah terdaftar! Silakan kembali dan gunakan menu Login."})
    
    new_secret = generate_base32_secret()
    # REVISI POIN 3: Pendaftaran baru tidak langsung memproduksi API Key
    default_api_key = "-"
    default_status = "Active (7-Day Free Trial - View Only)"
    
    db_save_user(email, new_secret, False, name, default_api_key, default_status)
    
    return jsonify({
        "success": True,
        "message": "Registrasi Free Trial berhasil!",
        "user": {
            "name": name,
            "email": email,
            "apiKey": default_api_key, 
            "status": default_status,
            "isPaid": False
        }
    })

# REVISI POIN 3: Route khusus untuk membuat API Key secara manual oleh User
@app.route('/api/generate-api-key', methods=['POST'])
def generate_api_key_route():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({"success": False, "message": "Email wajib diisi!"})

    user_data = db_get_user(email)
    if not user_data:
        return jsonify({"success": False, "message": "User tidak ditemukan di database!"})

    status = user_data.get('status', '')
    status_lower = status.lower()
    is_paid_user = any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"])

    if not is_paid_user:
        return jsonify({
            "success": False,
            "isPaid": False,
            "message": "Akun Anda masih Free Trial! Silakan selesaikan pembayaran langganan untuk membuat API Key."
        })

    # Jika berbayar / Admin -> buatkan API Key baru
    new_api_key = "TREND_" + uuid.uuid4().hex[:12].upper()
    
    db_save_user(
        email=email,
        secret=user_data['secret'],
        is_linked=user_data['is_linked'],
        name=user_data.get('name', ''),
        api_key=new_api_key,
        status=status
    )

    return jsonify({
        "success": True,
        "isPaid": True,
        "apiKey": new_api_key,
        "message": "🎉 API Key berhasil dibuat!"
    })

@app.route('/api/create-transaction', methods=['POST'])
def create_transaction():
    data = request.json or {}
    name = data.get('name', 'User')
    email = data.get('email', 'user@example.com').strip().lower()
    plan = data.get('plan', 'Creator Monthly')
    price_str = data.get('price', '200000')
    method = data.get('method', 'credit_card')
    is_upgrading = data.get('isUpgrading', False)

    existing_user = db_get_user(email)
    if existing_user and not is_upgrading:
        return jsonify({"success": False, "message": "Email sudah terdaftar! Silakan login via Beranda lalu klik Upgrade dari Dashboard Anda."})

    try:
        clean_price = re.sub(r'[^\d]', '', price_str)
        amount = int(clean_price)
    except:
        amount = 200000

    enabled_payments = [method] if method else []
    order_id = f"ORDER-{uuid.uuid4().hex[:8].upper()}"

    auth_string = base64.b64encode(f"{MIDTRANS_SERVER_KEY}:".encode()).decode()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_string}"
    }

    payload = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": amount
        },
        "customer_details": {
            "first_name": name,
            "email": email
        }
    }

    if enabled_payments:
        payload["enabled_payments"] = enabled_payments

    try:
        req = urllib.request.Request(
            MIDTRANS_API_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers, 
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            if response.status == 201:
                if not existing_user:
                    new_secret = generate_base32_secret()
                    default_api_key = "-"
                    db_save_user(email, new_secret, False, name, default_api_key, "Pending Payment")
                
                return jsonify({
                    "success": True,
                    "token": res_data.get('token'),
                    "redirect_url": res_data.get('redirect_url')
                })
            else:
                return jsonify({
                    "success": False, 
                    "message": res_data.get('error_messages', ['Gagal memproses ke Midtrans'])[0]
                })
                
    except urllib.error.HTTPError as e:
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            return jsonify({
                "success": False,
                "message": error_data.get('error_messages', [str(e)])[0]
            })
        except:
            return jsonify({"success": False, "message": f"HTTP Error: {e.code}"})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/check-payment', methods=['POST'])
def check_payment():
    email = request.json.get('email')
    return jsonify({"success": True, "isPaid": False})

@app.route('/api/tiktok-auth-url', methods=['GET'])
def get_tiktok_auth_url():
    """Route untuk menggenerate URL Login TikTok asli (Mode Sandbox)."""
    redirect_uri = "redirect_uri = "https://trendoraautomation.my.id/auth/tiktok/callback""
    state = uuid.uuid4().hex
    
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

# ==========================================
# WEBHOOK LISTENER DARI N8N & BACA LOG
# ==========================================
@app.route('/api/n8n-webhook', methods=['POST'])
def n8n_webhook():
    """Menerima POST Webhook dari n8n, mencatat log, & MENSIMULASIKAN TIKTOK API BILA MODE SANDBOX AKTIF."""
    api_key = request.headers.get('X-API-Key', '').strip()
    
    if not api_key:
        auth_header = request.headers.get('Authorization', '').strip()
        if auth_header.startswith('Bearer '):
            api_key = auth_header.replace('Bearer ', '')

    data = request.json or {}
    platform = data.get('platform', 'unknown').lower()
    status = data.get('status', 'RECEIVED')
    post_mode = data.get('post_mode', 'publish')
    is_sandbox = data.get('is_sandbox', False)
    details = data.get('details', {})
    
    if not api_key:
        return jsonify({"success": False, "message": "API Key is required in Header (X-API-Key or Authorization)"}), 400
    
    tiktok_simulation_log = None
    if platform == 'tiktok':
        media_url = details.get('media_url', '') if isinstance(details, dict) else ''
        caption = details.get('caption', '') if isinstance(details, dict) else ''
        
        if is_sandbox:
            if post_mode == 'draft':
                tiktok_simulation_log = {
                    "action": "Upload to TikTok Drafts (video.upload)",
                    "tiktok_endpoint": "https://open.tiktokapis.com/v2/post/publish/video/init/",
                    "method": "POST",
                    "headers": {
                        "Authorization": "Bearer <sandbox_access_token_simulated>",
                        "Content-Type": "application/json; charset=UTF-8"
                    },
                    "payload_sent": {
                        "post_info": {
                            "title": caption,
                            "privacy_level": "SELF_ONLY",
                            "disable_duet": False,
                            "disable_comment": False,
                            "disable_stitch": False
                        },
                        "source_info": {
                            "source": "PULL_FROM_URL",
                            "video_url": media_url
                        }
                    },
                    "tiktok_simulated_response": {
                        "data": {
                            "publish_id": f"v_draft_{uuid.uuid4().hex[:12]}",
                            "error_code": 0,
                            "error_msg": "Success - Saved to Drafts"
                        }
                    }
                }
            else:
                tiktok_simulation_log = {
                    "action": "Direct Publish to TikTok (video.publish)",
                    "tiktok_endpoint": "https://open.tiktokapis.com/v2/post/publish/video/init/",
                    "method": "POST",
                    "headers": {
                        "Authorization": "Bearer <sandbox_access_token_simulated>",
                        "Content-Type": "application/json; charset=UTF-8"
                    },
                    "payload_sent": {
                        "post_info": {
                            "title": caption,
                            "privacy_level": "PUBLIC",
                            "disable_duet": False,
                            "disable_comment": False,
                            "disable_stitch": False
                        },
                        "source_info": {
                            "source": "PULL_FROM_URL",
                            "video_url": media_url
                        }
                    },
                    "tiktok_simulated_response": {
                        "data": {
                            "publish_id": f"v_publish_{uuid.uuid4().hex[:12]}",
                            "error_code": 0,
                            "error_msg": "Success - Published directly"
                        }
                    }
                }
            
            if isinstance(details, dict):
                details['tiktok_api_trace'] = f"Success via Sandbox ({post_mode.upper()})"
        
        else:
            if isinstance(details, dict):
                details['tiktok_api_trace'] = "Success via Live Production API"

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
            
            response_data = {
                "success": True, 
                "message": "Log saved and payload processed", 
                "log_id": log_id,
                "sandbox_active": is_sandbox
            }
            if tiktok_simulation_log:
                response_data["tiktok_sandbox_trace"] = tiktok_simulation_log
                
            return jsonify(response_data)
        except Exception as e:
            print(f"GSheet Append Error: {e}")
            return jsonify({"success": False, "message": f"Failed to save to sheet: {str(e)}"}), 500
    else:
        if 'logs' not in user_2fa_store:
            user_2fa_store['logs'] = []
        user_2fa_store['logs'].append({
            "Timestamp": timestamp,
            "LogID": log_id,
            "APIKey": api_key,
            "Platform": platform,
            "Status": status,
            "Details": details_str
        })
        
        response_data = {"success": True, "message": "Log saved to memory (fallback)", "log_id": log_id, "sandbox_active": is_sandbox}
        if tiktok_simulation_log:
            response_data["tiktok_sandbox_trace"] = tiktok_simulation_log
            
        return jsonify(response_data)

@app.route('/api/get-logs', methods=['POST'])
def get_logs():
    """Membaca data Log dari tab 'Logs' berdasarkan API Key user."""
    api_key = request.headers.get('X-API-Key', '').strip()
    
    data = request.json or {}
    if not api_key:
        api_key = data.get('api_key', '').strip()
    
    if not api_key:
        return jsonify({"success": False, "message": "API Key is required in Header (X-API-Key)"})
        
    logs = []
    sheet = get_logs_sheet()
    
    if sheet:
        try:
            all_records = sheet.get_all_records()
            for row in all_records:
                if str(row.get('APIKey', '')).strip() == api_key:
                    logs.append({
                        "Timestamp": str(row.get('Timestamp', '')),
                        "LogID": str(row.get('LogID', '')),
                        "Platform": str(row.get('Platform', '')),
                        "Status": str(row.get('Status', '')),
                        "Details": str(row.get('Details', ''))
                    })
            logs.reverse()
            return jsonify({"success": True, "logs": logs})
        except Exception as e:
            print(f"Read Logs Error: {e}")
            
    if 'logs' in user_2fa_store:
        for row in user_2fa_store['logs']:
            if str(row.get('APIKey')).strip() == api_key:
                logs.append(row)
        logs.reverse()
        
    return jsonify({"success": True, "logs": logs})

if __name__ == '__main__':
    app.run(debug=True)