from flask import jsonify, render_template
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
        try:
            return render_template('index.html'), 200
        except Exception:
            return jsonify({"success": False, "message": "Endpoint / Halaman tidak ditemukan (404)."}), 200

    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({"success": False, "message": "Terjadi kesalahan internal pada server (500)."}), 200

    @app.errorhandler(Exception)
    def handle_global_exception(e):
        print(f"[Global Exception Handler]: {e}")
        return jsonify({"success": False, "message": f"Terjadi kesalahan server: {str(e)}"}), 200