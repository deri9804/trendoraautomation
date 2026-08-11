"""
===============================================================================
routes/__init__.py - Routes Initializer & Blueprint Registration
===============================================================================
Menggabungkan dan mendaftarkan semua Blueprint (pages, auth, oauth, webhook)
ke dalam aplikasi Flask utama.
"""

from .pages import pages_bp
from .auth import auth_bp
from .oauth_social import oauth_bp
from .webhook_n8n import webhook_bp

def register_routes(app):
    """Mendaftarkan seluruh blueprint ke instance Flask app."""
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(oauth_bp)
    app.register_blueprint(webhook_bp)
    print("[routes] Semua Blueprint berhasil didaftarkan.")