import os
import sys
from datetime import timedelta
from flask import Flask, jsonify, request

import config
from routes.pages import pages_bp
from routes.auth import auth_bp
from routes.webhook_n8n import webhook_bp
from routes.oauth_social import oauth_bp

# Inisialisasi Aplikasi Flask
app = Flask(__name__)

# CRITICAL FIX: Pasang secret_key untuk mengaktifkan Flask Session
app.secret_key = getattr(config, 'SECRET_KEY', os.environ.get("SECRET_KEY", "trendora_secure_session_key_2026_x89a"))

# Konfigurasi cookie sesi
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set True jika full HTTPS production

# Register All Route Blueprints
app.register_blueprint(pages_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(oauth_bp)

# Global CORS Handler
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-API-Key,X-User-Email'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"success": False, "message": "Resource not found (404)"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "message": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)