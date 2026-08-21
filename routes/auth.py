import os
import sys
import re
from datetime import datetime, timedelta

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Blueprint, request, jsonify
import urllib.parse
import uuid

import config
from utils import database as db
from utils import security as sec

auth_bp = Blueprint('auth', __name__)

def generate_50char_api_key():
    """Generates a formatted API Key with prefix TRD- and exact total length of 50 characters."""
    raw = (uuid.uuid4().hex + uuid.uuid4().hex).upper()
    return f"TRD-{raw[:5]}-{raw[5:10]}-{raw[10:15]}-{raw[15:20]}-{raw[20:25]}-{raw[25:30]}-{raw[30:35]}-{raw[35:39]}"

def check_user_trial_status(user_data):
    if not user_data:
        return {"is_paid": False, "is_trial": False, "is_expired": True, "days_left": 0, "status_text": "Expired"}
    
    status_str = user_data.get('status', '')
    status_lower = status_str.lower()
    
    if any(word in status_lower for word in ["paid", "subscriber", "admin", "lifetime"]):
        return {"is_paid": True, "is_trial": False, "is_expired": False, "days_left": 999, "status_text": "Active (Paid Subscriber)"}
    
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
            
            if not user_data.get('is_linked'):
                db.db_save_user(email, secret, True, name, api_key, user_data.get('status', ''))
                
            trial_info = check_user_trial_status(user_data)
            
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
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_trial = f"Free Trial ({now_str})"
        initial_api_key = generate_50char_api_key()
        
        # Simpan ke Google Sheets
        is_saved = db.db_save_user(email, new_secret, False, name, initial_api_key, status_trial)
        
        if not is_saved:
            return jsonify({
                "success": False, 
                "message": "Gagal menyimpan data ke Google Sheets! Harap periksa variabel GOOGLE_APPLICATION_CREDENTIALS_JSON di Vercel."
            }), 500

        return jsonify({
            "success": True, 
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

        trial_info = check_user_trial_status(user_data)

        if trial_info["is_expired"] and not trial_info["is_paid"]:
            return jsonify({
                "success": False, 
                "isPaid": False, 
                "isExpired": True,
                "message": "Masa Free Trial 1 Minggu Anda sudah habis! Silakan upgrade akun ke berbayar untuk membuat API Key baru."
            }), 200

        new_api_key = generate_50char_api_key()
        db.db_save_user(email, user_data.get('secret', ''), user_data.get('is_linked', False), user_data.get('name', ''), new_api_key, user_data.get('status', ''))
        return jsonify({
            "success": True, 
            "isPaid": trial_info["is_paid"], 
            "isExpired": False,
            "apiKey": new_api_key
        }), 200
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
        
        trial_info = check_user_trial_status(user_data)
        
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
                "name": user_data.get('name', ''),
                "email": email,
                "apiKey": user_data.get('api_key', '-'),
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