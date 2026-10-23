import os
import sys
from datetime import timedelta
from flask import Flask, jsonify, request

import config
from routes.pages import pages_bp
from routes.auth import auth_bp
from routes.webhook_n8n import webhook_bp
from routes.oauth_social import oauth_bp
from routes.instagram_auto_dm import ig_auto_dm_bp

# Inisialisasi Aplikasi Flask
app = Flask(__name__)

# CRITICAL FIX: Pasang secret_key untuk mengaktifkan Flask Session
app.secret_key = getattr(config, 'SECRET_KEY', os.environ.get("SECRET_KEY", "trendora_secure_session_key_2026_x89a"))

# Konfigurasi cookie sesi
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Otomatis aktifkan Secure Cookie jika running di Vercel HTTPS
app.config['SESSION_COOKIE_SECURE'] = bool(os.environ.get('VERCEL') or os.environ.get('SESSION_COOKIE_SECURE', '').lower() == 'true')

# Register All Route Blueprints
app.register_blueprint(pages_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(oauth_bp)
app.register_blueprint(ig_auto_dm_bp)

# Global Security Headers & CORS Handler
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Batasi CORS untuk headers yang diizinkan
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-API-Key'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    # Cegah browser caching untuk dashboard agar perubahan live selalu terupdate
    if request.path in ['/dashboard', '/', '/api/instagram-auto-dm/settings']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"success": False, "message": "Resource not found (404)"}), 404

@app.errorhandler(500)
def server_error(e):
    # SECURITY FIX: Jangan pernah bocorkan internal traceback/error str(e) ke user/client publik!
    print(f"[Internal Server Error 500]: {e}")
    return jsonify({"success": False, "message": "Terjadi kendala pada server (500). Silakan hubungi admin."}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)