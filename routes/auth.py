import os
import sys

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTILS_DIR = os.path.join(PARENT_DIR, 'utils')
for d in [PARENT_DIR, UTILS_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

from flask import Blueprint, request, jsonify
import urllib.parse
import uuid

try:
    import config
    import database as db
    import security as sec
except ImportError:
    try:
        from utils import config, database as db, security as sec
    except ImportError:
        import config
        import database as db
        import security as sec

auth_bp = Blueprint('auth', __name__)

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
            db.db_save_user(email, secret, user_data.get('is_linked', False), user_data.get('name', ''), user_data.get('api_key', ''), user_data.get('status', ''))

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
            api_key = user_data.get('api_key') or "-"
            status = user_data.get('status') or "Active"
            
            if not user_data.get('is_linked'):
                db.db_save_user(email, secret, True, name, api_key, status)
                
            status_lower = status.lower()
            is_paid_user = any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"])
            
            connected_platforms = []
            if user_data.get('tiktok_connected'): connected_platforms.append('TikTok')
            if user_data.get('meta_connected'):
                connected_platforms.append('Facebook')
                connected_platforms.append('Instagram')
            if user_data.get('linkedin_connected'): connected_platforms.append('LinkedIn')
            if user_data.get('youtube_connected'): connected_platforms.append('YouTube')
            if user_data.get('threads_connected'): connected_platforms.append('Threads')
            if user_data.get('twitter_connected'): connected_platforms.append('Twitter')
            
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
            }), 200
        return jsonify({"success": False, "message": "Kode OTP salah atau sudah kadaluarsa!"}), 200
    except Exception as e:
        print(f"[Error /api/verify-otp]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/reset-2fa-qr', methods=['POST', 'OPTIONS'])
def reset_2fa_qr():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()
        if not email:
            return jsonify({"success": False, "message": "Email wajib diisi!"}), 200

        old_data = db.db_get_user(email)
        if not old_data:
            return jsonify({"success": False, "message": "Email tidak ditemukan!"}), 200
        
        new_secret = sec.generate_base32_secret()
        issuer = "TRENDORA"
        totp_uri = f"otpauth://totp/{issuer}:{email}?secret={new_secret}&issuer={issuer}"
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(totp_uri)}"
        
        is_sent = sec.send_email_qr(email, qr_code_url, new_secret)
        
        if is_sent:
            db.db_save_user(email, new_secret, True, old_data.get('name', ''), old_data.get('api_key', ''), old_data.get('status', ''))
            return jsonify({"success": True, "message": "QR Code 2FA baru telah dikirim ke Email Anda! Silakan cek Inbox/Spam."}), 200
        else:
            return jsonify({"success": False, "message": "Gagal mengirim email. Pastikan Environment SMTP_PASSWORD sudah diatur di Vercel."}), 200
    except Exception as e:
        print(f"[Error /api/reset-2fa-qr]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/register-trial', methods=['POST', 'OPTIONS'])
def register_trial():
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
        db.db_save_user(email, new_secret, False, name, "-", "Active (7-Day Free Trial - View Only)")
        return jsonify({"success": True, "message": "Registrasi berhasil", "user": {"name": name, "email": email, "apiKey": "-", "isPaid": False}}), 200
    except Exception as e:
        print(f"[Error /api/register-trial]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/generate-api-key', methods=['POST', 'OPTIONS'])
def generate_api_key_route():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()
        if not email:
            return jsonify({"success": False, "message": "Email wajib diisi!"}), 200

        user_data = db.db_get_user(email)
        if not user_data:
            return jsonify({"success": False, "message": "User tidak ditemukan!"}), 200

        status_lower = user_data.get('status', '').lower()
        is_paid_user = any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"])

        if not is_paid_user:
            return jsonify({"success": False, "isPaid": False, "message": "Akun Free Trial, upgrade untuk unlock API Key!"}), 200

        new_api_key = "TREND_" + uuid.uuid4().hex[:12].upper()
        db.db_save_user(email, user_data.get('secret', ''), user_data.get('is_linked', False), user_data.get('name', ''), new_api_key, user_data.get('status', ''))
        return jsonify({"success": True, "isPaid": True, "apiKey": new_api_key}), 200
    except Exception as e:
        print(f"[Error /api/generate-api-key]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200

@auth_bp.route('/api/me', methods=['POST', 'OPTIONS'])
def get_me():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip().lower()
        if not email:
            return jsonify({"success": False, "message": "Email wajib diisi!"}), 200
        
        user_data = db.db_get_user(email)
        if not user_data:
            return jsonify({"success": False, "message": "User tidak ditemukan!"}), 200
        
        connected_platforms = []
        if user_data.get('tiktok_connected'): connected_platforms.append('TikTok')
        if user_data.get('meta_connected'):
            connected_platforms.append('Facebook')
            connected_platforms.append('Instagram')
        if user_data.get('linkedin_connected'): connected_platforms.append('LinkedIn')
        if user_data.get('youtube_connected'): connected_platforms.append('YouTube')
        if user_data.get('threads_connected'): connected_platforms.append('Threads')
        if user_data.get('twitter_connected'): connected_platforms.append('Twitter')
            
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
        }), 200
    except Exception as e:
        print(f"[Error /api/me]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200