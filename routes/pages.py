"""
===============================================================================
routes/pages.py - Frontend View Page Routes
===============================================================================
Blueprint untuk menyajikan tampilan HTML utama:
- Index / Landing Page
- Login Page
- Checkout Page
- Dashboard Page
- Webhook Page
- Terms of Service (TOS), Privacy Policy, Data Deletion
"""

from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    return render_template('index.html')

@pages_bp.route('/login')
def login_page():
    return render_template('login.html')

@pages_bp.route('/checkout')
def checkout_page():
    return render_template('checkout.html')

@pages_bp.route('/dashboard')
def dashboard_page():
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