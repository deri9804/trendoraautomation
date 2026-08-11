"""
===============================================================================
app.py - Main Application Entrypoint
===============================================================================
File entrypoint utama aplikasi Flask Trendora Automation.
Seluruh routing dialihkan ke folder /routes menggunakan Blueprint.
"""

from flask import Flask
from flask_cors import CORS
from routes import register_routes

app = Flask(__name__)
CORS(app)

# Registrasi seluruh Blueprint dari package routes
register_routes(app)

if __name__ == '__main__':
    app.run(debug=True)