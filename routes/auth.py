import os
import sys
import re
from datetime import datetime, timedelta

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Blueprint, request, jsonify, session, current_app
import urllib.parse
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config
from utils import database as db
from utils import security as sec

auth_bp = Blueprint('auth', __name__)

def ensure_app_secret_key():
    """Memastikan Flask app memiliki secret_key aktif untuk mencegah session runtime error."""
    try:
        if not current_app.secret_key:
            current_app.secret_key = getattr(
                config, 
                'SECRET_KEY', 
                os.environ.get("SECRET_KEY", "trendora_secure_session_key_2026_x89a")
            )
    except Exception as e:
        print(f"[Session Warning]: {e}")

def send_2fa_reset_email(to_email, secret, qr_code_url, user_name="User"):
    """Mengirimkan email instruksi reset 2FA berisi QR Code dan Setup Key via SMTP."""
    smtp_user = getattr(config, 'SMTP_EMAIL', os.environ.get('SMTP_EMAIL', 'trendoraautomation@gmail.com'))
    smtp_pass = getattr(config, 'SMTP_PASSWORD', os.environ.get('SMTP_PASSWORD', ''))
    
    if not smtp_user or not smtp_pass:
        print("[SMTP Warning]: SMTP_EMAIL atau SMTP_PASSWORD belum dikonfigurasi di environment variables!")
        return False, "Kredensial SMTP server (SMTP_EMAIL / SMTP_PASSWORD) belum diisi di environment variables."

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🔐 Reset Google Authenticator (2FA) - TRENDORA"
        msg['From'] = f"TRENDORA Security <{smtp_user}>"
        msg['To'] = to_email

        formatted_secret = " ".join([secret[i:i+4] for i in range(0, len(secret), 4)])

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
        </head>
        <body style="background-color: #0d0a1a; margin: 0; padding: 24px; font-family: 'Inter', Arial, sans-serif; color: #ffffff;">
          <div style="max-width: 520px; margin: 0 auto; background-color: #0f1524; border: 1px solid rgba(236,72,153,0.4); border-radius: 16px; padding: 32px 24px; color: #ffffff; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <div style="margin-bottom: 20px;">
              <span style="background-color: rgba(236, 72, 153, 0.2); color: #ec4899; padding: 6px 14px; border-radius: 20px; font-size: 11px; font-weight: bold; letter-spacing: 1px; display: inline-block;">⚡ TRENDORA SECURITY</span>
              <h2 style="color: #ffffff; font-size: 22px; margin: 16px 0 6px 0; font-weight: 800;">Reset Google Authenticator (2FA)</h2>
              <p style="color: #9ca3af; font-size: 13px; margin: 0; line-height: 1.5;">Halo <strong>{user_name}</strong>, kami telah membuatkan kunci 2FA baru untuk akun Anda ({to_email}).</p>
            </div>

            <div style="background-color: #ffffff; padding: 14px; border-radius: 12px; display: inline-block; margin: 16px 0; border: 2px solid #ec4899;">
              <img src="{qr_code_url}" alt="Google Authenticator QR Code" width="180" height="180" style="display: block; border-radius: 6px;" />
            </div>

            <p style="color: #d1d5db; font-size: 13px; line-height: 1.6; margin: 12px 0 16px 0;">
              1. Buka aplikasi <strong>Google Authenticator</strong> di ponsel Anda.<br>
              2. Tekan tombol <strong>(+)</strong> lalu pilih <strong>Scan a QR code</strong> ke gambar di atas.
            </p>

            <div style="margin-top: 16px; text-align: left; background-color: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 14px;">
              <div style="font-size: 11px; color: #9ca3af; margin-bottom: 4px;">Atau masukkan <strong>Setup Key</strong> manual jika tidak bisa scan QR:</div>
              <div style="font-family: monospace; font-size: 15px; color: #38bdf8; font-weight: bold; letter-spacing: 2px; word-break: break-all;">{formatted_secret}</div>
            </div>

            <p style="color: #f87171; font-size: 11px; margin-top: 24px; line-height: 1.5;">
              ⚠️ Jangan bagikan email ini atau Setup Key di atas kepada siapa pun demi keamanan akun Anda.
            </p>

            <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.08); font-size: 11px; color: #6b7280;">
              &copy; 2026 TRENDORA AUTOMATION Inc. All rights reserved.
            </div>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=12) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_email, msg.as_string())
        except Exception:
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=12) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_email, msg.as_string())

        print(f"[SMTP Success]: QR Code 2FA berhasil dikirim ke email {to_email}")
        return True, "Email berhasil dikirim."
    except Exception as e:
        print(f"[SMTP Send Error]: {e}")
        return False, str(e)

def generate_50char_api_key():
    """Menghasilkan API Key dengan prefix TRD- dan panjang total terstandarisasi 50 karakter."""
    raw = (uuid.uuid4().hex + uuid.uuid4().hex).upper()
    return f"TRD-{raw[:5]}-{raw[5:10]}-{raw[10:15]}-{raw[15:20]}-{raw[20:25]}-{raw[25:30]}-{raw[30:35]}-{raw[35:39]}"

def check_user_trial_status(user_data):
    """Memeriksa apakah akun berstatus Paid, Trial Aktif (1-7 Hari), atau Trial Expired."""
    if not user_data:
        return {"is_paid": False, "is_trial": False, "is_expired": True, "days_left": 0, "status_text": "Expired"}
    
    status_str = user_data.get('status', '')
    status_lower = status_str.lower()
    
    # Pengguna berbayar atau admin
    if any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"]):
        return {"is_paid": True, "is_trial": False, "is_expired": False, "days_left": 999, "status_text": "Active (Paid Subscriber)"}
    
    # Menghitung masa 7 hari dari tanggal registrasi
    match = re.search(r'\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?', status_str)
    if match:
        date_str = match.group(0)
        try:
            if " " in date_str:
                reg_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:
                reg_date = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            reg_date = datetime.now()
    else:
        reg_date = datetime.now()
        
    expiry_date = reg_date + timedelta(days=7)
    now = datetime.now()
    
    if now >= expiry_date:
        return {
            "is_paid": False, 
            "is_trial": True, 
            "is_expired": True, 
            "days_left": 0, 
            "status_text": "Free Trial Expired (Masa Uji Coba Habis)",
            "reg_date": reg_date.strftime("%d/%m/%Y")
        }
    else:
        time_diff = expiry_date - now
        days_left = max(1, time_diff.days + (1 if time_diff.seconds > 0 else 0))
        return {
            "is_paid": False, 
            "is_trial": True, 
            "is_expired": False, 
            "days_left": days_left, 
            "status_text": f"Active (7-Day Free Trial - Sisa {days_left} Hari)",
            "reg_date": reg_date.strftime("%d/%m/%Y")
        }

@auth_bp.route('/api/request-otp', methods=['POST', 'OPTIONS'])
def request_otp():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()
        if not email:
            return jsonify({"success": False, "message": "Email wajib diisi!"}), 200
        
        user_data = db.db_get_user(email)
        if not user_data:
            return jsonify({"success": False, "message": "Email belum terdaftar!"}), 200
        
        secret = user_data.get('secret')
        if not secret:
            secret = sec.generate_base32_secret()
            db.db_save_user(
                email, 
                secret, 
                user_data.get('is_linked', False), 
                user_data.get('name', ''), 
                user_data.get('api_key', ''), 
                user_data.get('status', '')
            )

        is_linked = user_data.get('is_linked', False)
        
        if not is_linked:
            issuer = "TRENDORA"
            totp_uri = f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}"
            qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(totp_uri)}"
            return jsonify({"success": True, "is2faLinked": False, "qrCodeUrl": qr_code_url}), 200
        else:
            return jsonify({"success": True, "is2faLinked": True}), 200
    except Exception as e:
        print(f"[Error /api/request-otp]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/verify-otp', methods=['POST', 'OPTIONS'])
def verify_otp_route():
    ensure_app_secret_key()
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()
        otp = data.get('otp', '').strip()
        if not email or not otp:
            return jsonify({"success": False, "message": "Data tidak lengkap!"}), 200
            
        user_data = db.db_get_user(email)
        if not user_data:
            return jsonify({"success": False, "message": "Email belum terdaftar!"}), 200
            
        secret = user_data.get('secret', '')
        if not secret:
            return jsonify({"success": False, "message": "Secret 2FA tidak ditemukan pada akun ini!"}), 200

        is_valid = sec.verify_totp(secret, otp)
        if is_valid:
            name = user_data.get('name') or email.split('@')[0].capitalize()
            api_key = user_data.get('api_key', '').strip()
            trial_info = check_user_trial_status(user_data)
            
            # Jika user belum memiliki API Key aktif dan trial masih aktif, buatkan otomatis
            if (not api_key or api_key == '-' or '•' in api_key) and not trial_info["is_expired"]:
                api_key = generate_50char_api_key()
            
            # Simpan status verifikasi akun
            db.db_save_user(email, secret, True, name, api_key, user_data.get('status', ''))
                
            # Mendeteksi platform yang sudah terhubung
            connected_platforms = []
            if user_data.get('tiktok_connected'): connected_platforms.append('TikTok')
            if user_data.get('meta_connected'):
                connected_platforms.append('Facebook')
                connected_platforms.append('Instagram')
            if user_data.get('linkedin_connected'): connected_platforms.append('LinkedIn')
            if user_data.get('youtube_connected'): connected_platforms.append('YouTube')
            if user_data.get('threads_connected'): connected_platforms.append('Threads')
            if user_data.get('twitter_connected'): connected_platforms.append('Twitter')
            
            session_token = uuid.uuid4().hex
            session['user_email'] = email
            session['session_token'] = session_token
            session.permanent = True
            
            return jsonify({
                "success": True, 
                "sessionToken": session_token,
                "user": {
                    "name": name, 
                    "email": email, 
                    "apiKey": api_key, 
                    "status": trial_info["status_text"], 
                    "isPaid": trial_info["is_paid"],
                    "isTrial": trial_info["is_trial"],
                    "isExpired": trial_info["is_expired"],
                    "daysLeft": trial_info["days_left"],
                    "connectedPlatforms": connected_platforms
                }
            }), 200
        return jsonify({"success": False, "message": "Kode OTP salah atau sudah kadaluarsa!"}), 200
    except Exception as e:
        print(f"[Error /api/verify-otp]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/reset-2fa', methods=['POST', 'OPTIONS'])
@auth_bp.route('/api/reset-2fa-qr', methods=['POST', 'OPTIONS'])
def reset_2fa():
    """Endpoint untuk mereset secret 2FA pengguna jika kehilangan akses Google Authenticator."""
    ensure_app_secret_key()
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()
        if not email:
            email = session.get('user_email', '').strip().lower()
            
        if not email:
            return jsonify({"success": False, "message": "Email wajib diisi untuk mereset 2FA!"}), 200
            
        user_data = db.db_get_user(email)
        if not user_data:
            return jsonify({"success": False, "message": "Email tidak terdaftar di sistem!"}), 200

        new_secret = sec.generate_base32_secret()
        name = user_data.get('name', 'User')
        api_key = user_data.get('api_key', '')
        status = user_data.get('status', '')
        
        # Simpan secret key baru ke Google Sheets
        db.db_save_user(email, new_secret, False, name, api_key, status)
        
        # Buat URI dan QR Code URL untuk Google Authenticator
        issuer = "TRENDORA"
        totp_uri = f"otpauth://totp/{issuer}:{email}?secret={new_secret}&issuer={issuer}"
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(totp_uri)}"

        # Kirim QR Code & Setup Key ke email pengguna
        email_sent, email_err = send_2fa_reset_email(email, new_secret, qr_code_url, user_name=name)

        if email_sent:
            return jsonify({
                "success": True, 
                "message": f"QR Code 2FA baru telah dikirim ke email {email}. Silakan buka kotak masuk/spam email Anda, scan di Google Authenticator, lalu masukkan 6 digit OTP di form login!"
            }), 200
        else:
            return jsonify({
                "success": False, 
                "message": f"Kunci 2FA berhasil dibuat di database, namun email gagal dikirim: {email_err}. Pastikan variabel SMTP_PASSWORD (App Password Gmail) sudah disetel di Vercel."
            }), 200

    except Exception as e:
        print(f"[Error /api/reset-2fa]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/register-trial', methods=['POST', 'OPTIONS'])
def register_trial():
    ensure_app_secret_key()
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()
        name = data.get('name', 'User').strip()
        if not email:
            return jsonify({"success": False, "message": "Email wajib diisi!"}), 200

        existing_user = db.db_get_user(email)
        if existing_user:
            return jsonify({"success": False, "message": "Email sudah terdaftar!"}), 200
        
        new_secret = sec.generate_base32_secret()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_trial = f"Free Trial ({now_str})"
        initial_api_key = generate_50char_api_key()
        
        # Simpan ke Google Sheets
        is_saved = db.db_save_user(email, new_secret, False, name, initial_api_key, status_trial)
        
        if not is_saved:
            return jsonify({
                "success": False, 
                "message": "Gagal menyimpan data ke Google Sheets! Harap periksa variabel kredensial."
            }), 500

        # Simpan sesi pengguna baru
        session_token = uuid.uuid4().hex
        session['user_email'] = email
        session['session_token'] = session_token
        session.permanent = True

        return jsonify({
            "success": True, 
            "sessionToken": session_token,
            "message": "Registrasi Free Trial 1 Minggu berhasil!", 
            "user": {
                "name": name, 
                "email": email, 
                "apiKey": initial_api_key, 
                "isPaid": False,
                "isTrial": True,
                "isExpired": False,
                "daysLeft": 7
            }
        }), 200
    except Exception as e:
        print(f"[Error /api/register-trial]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/generate-api-key', methods=['POST', 'OPTIONS'])
def generate_api_key_route():
    ensure_app_secret_key()
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()
        
        # Validasi sesi aktif
        if not email:
            email = session.get('user_email', '').strip().lower()

        if not email:
            return jsonify({"success": False, "message": "Sesi tidak valid atau email tidak ditemukan!"}), 401

        user_data = db.db_get_user(email)
        if not user_data:
            return jsonify({"success": False, "message": "User tidak ditemukan!"}), 200

        trial_info = check_user_trial_status(user_data)

        if trial_info["is_expired"] and not trial_info["is_paid"]:
            return jsonify({
                "success": False, 
                "isPaid": False, 
                "isExpired": True,
                "message": "Masa Free Trial 7 Hari Anda sudah habis! Silakan upgrade akun ke berbayar untuk membuat API Key baru."
            }), 200

        new_api_key = generate_50char_api_key()
        db.db_save_user(
            email, 
            user_data.get('secret', ''), 
            user_data.get('is_linked', False), 
            user_data.get('name', ''), 
            new_api_key, 
            user_data.get('status', '')
        )
        return jsonify({
            "success": True, 
            "isPaid": trial_info["is_paid"], 
            "isExpired": False,
            "apiKey": new_api_key
        }), 200
    except Exception as e:
        print(f"[Error /api/generate-api-key]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/me', methods=['POST', 'GET', 'OPTIONS'])
def get_me():
    ensure_app_secret_key()
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        email = session.get('user_email', '').strip().lower()
        
        if not email and request.is_json:
            data = request.get_json(silent=True) or {}
            email = data.get('email', '').strip().lower()
            
        if not email:
            email = request.headers.get('X-User-Email', '').strip().lower()
            
        if not email:
            return jsonify({
                "success": False, 
                "authenticated": False,
                "message": "Sesi belum login atau telah berakhir."
            }), 401
        
        user_data = db.db_get_user(email)
        if not user_data:
            session.clear()
            return jsonify({
                "success": False, 
                "authenticated": False,
                "message": "User tidak ditemukan di database."
            }), 401
        
        trial_info = check_user_trial_status(user_data)
        api_key = (user_data.get('api_key') or '').strip()

        # JIKA TRIAL MASIH AKTIF TAPI API KEY BELUM TERBUAT (KOSONG ATAU "-"), GENERATE OTOMATIS
        if (not api_key or api_key == '-' or '•' in api_key) and not trial_info["is_expired"]:
            api_key = generate_50char_api_key()
            db.db_save_user(
                email,
                user_data.get('secret', ''),
                user_data.get('is_linked', False),
                user_data.get('name', ''),
                api_key,
                user_data.get('status', '')
            )
        
        connected_platforms = []
        if user_data.get('tiktok_connected'): connected_platforms.append('TikTok')
        if user_data.get('meta_connected'):
            connected_platforms.append('Facebook')
            connected_platforms.append('Instagram')
        if user_data.get('linkedin_connected'): connected_platforms.append('LinkedIn')
        if user_data.get('youtube_connected'): connected_platforms.append('YouTube')
        if user_data.get('threads_connected'): connected_platforms.append('Threads')
        if user_data.get('twitter_connected'): connected_platforms.append('Twitter')
        
        # Perbarui sesi server aktif
        session['user_email'] = email
        
        return jsonify({
            "success": True,
            "authenticated": True,
            "user": {
                "name": user_data.get('name', ''),
                "email": email,
                "apiKey": api_key,
                "status": trial_info["status_text"],
                "isPaid": trial_info["is_paid"],
                "isTrial": trial_info["is_trial"],
                "isExpired": trial_info["is_expired"],
                "daysLeft": trial_info["days_left"],
                "connectedPlatforms": connected_platforms
            }
        }), 200
    except Exception as e:
        print(f"[Error /api/me]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/logout', methods=['POST', 'GET'])
def logout_route():
    ensure_app_secret_key()
    session.clear()
    return jsonify({"success": True, "message": "Sesi berhasil dihapus dan ditutup secara aman."}), 200