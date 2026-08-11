import os
import sys

# Memastikan root directory terdaftar di sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask
from flask_cors import CORS
from routes import register_routes

# Mengatur template_folder dan static_folder dengan path absolut agar Vercel Serverless mengenali lokasi berkas
template_dir = os.path.join(BASE_DIR, 'templates')
static_dir = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

CORS(app)

# Mendaftarkan seluruh rute dan global error handler
register_routes(app)

if __name__ == '__main__':
    app.run(debug=True)