"""
===============================================================================
routes/auth.py - Authentication & User Management Routes
===============================================================================
Blueprint untuk otentikasi & manajemen pengguna:
- Request & Verify OTP 2FA
- Reset 2FA QR Code via Email
- Register Free Trial
- Generate API Key
- User Profile Info (/api/me)
"""

from flask import Blueprint, request, jsonify
import urllib.parse
import uuid
import config
import database as db
import security as sec

auth_bp = Blueprint('auth', __name__)

# =============================================================================
# ROUTE ENDPOINTS (AUTH & USER MANAGEMENT)
# =============================================================================

@auth_bp.route('/api/request-otp', methods=['POST'])
def request_otp():
    email = request.json.get('email', '').strip().lower()
    if not email:
        return jsonify({"success": False, "message": "Email wajib diisi!"})
    
    user_data = db.db_get_user(email)
    if not user_data:
        return jsonify({"success": False, "message": "Email belum terdaftar!"})
    
    secret = user_data['secret']
    is_linked = user_data['is_linked']
    
    if not is_linked:
        issuer = "TRENDORA"
        totp_uri = f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}"
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(totp_uri)}"
        return jsonify({"success": True, "is2faLinked": False, "qrCodeUrl": qr_code_url})
    else:
        return jsonify({"success": True, "is2faLinked": True})

@auth_bp.route('/api/verify-otp', methods=['POST'])
def verify_otp_route():
    email = request.json.get('email', '').strip().lower()
    otp = request.json.get('otp', '').strip()
    if not email or not otp:
        return jsonify({"success": False, "message": "Data tidak lengkap!"})
        
    user_data = db.db_get_user(email)
    if not user_data:
        return jsonify({"success": False, "message": "Email belum terdaftar!"})
        
    is_valid = sec.verify_totp(user_data['secret'], otp)
    if is_valid:
        name = user_data.get('name') or email.split('@')[0].capitalize()
        api_key = user_data.get('api_key') or "-"
        status = user_data.get('status') or "Active"
        
        if not user_data.get('is_linked'):
            db.db_save_user(email, user_data['secret'], True, name, api_key, status)
            
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
        })
    return jsonify({"success": False, "message": "OTP salah/kadaluarsa!"})

@auth_bp.route('/api/reset-2fa-qr', methods=['POST'])
def reset_2fa_qr():
    email = request.json.get('email', '').strip().lower()
    old_data = db.db_get_user(email)
    if not old_data:
        return jsonify({"success": False, "message": "Email tidak ditemukan!"})
    
    new_secret = sec.generate_base32_secret()
    issuer = "TRENDORA"
    totp_uri = f"otpauth://totp/{issuer}:{email}?secret={new_secret}&issuer={issuer}"
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(totp_uri)}"
    
    is_sent = sec.send_email_qr(email, qr_code_url, new_secret)
    
    if is_sent:
        db.db_save_user(email, new_secret, True, old_data.get('name', ''), old_data.get('api_key', ''), old_data.get('status', ''))
        return jsonify({"success": True, "message": "QR Code 2FA baru telah dikirim ke Email Anda! Silakan cek Inbox/Spam."})
    else:
        return jsonify({"success": False, "message": "Gagal mengirim email. Pastikan Environment SMTP_PASSWORD sudah diatur di Vercel."})

@auth_bp.route('/api/register-trial', methods=['POST'])
def register_trial():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', 'User').strip()
    
    existing_user = db.db_get_user(email)
    if existing_user:
        return jsonify({"success": False, "message": "Email sudah terdaftar!"})
    
    new_secret = sec.generate_base32_secret()
    db.db_save_user(email, new_secret, False, name, "-", "Active (7-Day Free Trial - View Only)")
    return jsonify({"success": True, "message": "Registrasi berhasil", "user": {"name": name, "email": email, "apiKey": "-", "isPaid": False}})

@auth_bp.route('/api/generate-api-key', methods=['POST'])
def generate_api_key_route():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    user_data = db.db_get_user(email)
    if not user_data:
        return jsonify({"success": False})

    status_lower = user_data.get('status', '').lower()
    is_paid_user = any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"])

    if not is_paid_user:
        return jsonify({"success": False, "isPaid": False, "message": "Akun Free Trial, upgrade untuk unlock!"})

    new_api_key = "TREND_" + uuid.uuid4().hex[:12].upper()
    db.db_save_user(email, user_data['secret'], user_data['is_linked'], user_data.get('name', ''), new_api_key, user_data.get('status', ''))
    return jsonify({"success": True, "isPaid": True, "apiKey": new_api_key})

@auth_bp.route('/api/me', methods=['POST'])
def get_me():
    email = request.json.get('email', '').strip().lower()
    if not email:
        return jsonify({"success": False})
    
    user_data = db.db_get_user(email)
    if not user_data:
        return jsonify({"success": False})
    
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
    })