from flask import Blueprint, render_template, redirect, url_for, session, Response

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    return render_template('index.html')

@pages_bp.route('/login')
def login_page():
    # Jika sudah login, langsung arahkan ke dashboard
    if session.get('user_email'):
        return redirect(url_for('pages.dashboard_page'))
    return render_template('login.html')

@pages_bp.route('/checkout')
def checkout_page():
    return render_template('checkout.html')

@pages_bp.route('/dashboard')
def dashboard_page():
    # SECURITY FIX: Server-side route guard (Tolak akses dashboard jika belum login)
    if not session.get('user_email'):
        return redirect(url_for('pages.login_page'))
    return render_template('dashboard.html')

@pages_bp.route('/webhook')
def webhook_page():
    return render_template('webhook.html')

@pages_bp.route('/tos')
def tos_page():
    return render_template('tos.html')

@pages_bp.route('/privacy')
def privacy_page():
    return render_template('privacy.html')

@pages_bp.route('/data-deletion')
def data_deletion_page():
    return render_template('data_deletion.html')

@pages_bp.route('/google73174c9969287988.html')
def google_verification_file():
    return Response("google-site-verification: google73174c9969287988.html", mimetype="text/html")
