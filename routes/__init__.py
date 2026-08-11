import os
import sys

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import jsonify
from .pages import pages_bp
from .auth import auth_bp
from .oauth_social import oauth_bp
from .webhook_n8n import webhook_bp

def register_routes(app):
    """Mendaftarkan seluruh blueprint ke instance Flask app dan memasang Global Error Handler."""
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(oauth_bp)
    app.register_blueprint(webhook_bp)

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"success": False, "message": "Endpoint / Halaman tidak ditemukan (404)."}), 404

    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({"success": False, "message": "Terjadi kesalahan internal pada server (500)."}), 500

    print("[routes] Semua Blueprint dan Global Error Handler berhasil didaftarkan.")