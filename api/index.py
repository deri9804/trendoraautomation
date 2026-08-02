import sys
import os

# Menambahkan root folder ke path biar bisa panggil app.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

# Vercel butuh variable 'app' untuk dieksekusi
app_instance = app