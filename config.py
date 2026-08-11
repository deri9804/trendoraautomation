import os
#konfigurasi gsheet
GOOGLE_SHEET_ID = "1P0zTEwtMmWfxhHAY6-QbQd5to6Id1rzazgel-PiSJwI" 
SERVICE_ACCOUNT_FILE = "service_account.json"
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON") # <--- Tambahin yang ini bro

# KONFIGURASI TIKTOK DEVELOPER
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET")

# KONFIGURASI META (FACEBOOK & INSTAGRAM)
META_CLIENT_ID = os.environ.get("META_CLIENT_ID")
META_CLIENT_SECRET = os.environ.get("META_CLIENT_SECRET")
META_WEBHOOK_VERIFY_TOKEN = os.environ.get("META_WEBHOOK_VERIFY_TOKEN", "trendora_meta_secret_123")

# KONFIGURASI LINKEDIN
LINKEDIN_CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")

# KONFIGURASI YOUTUBE / GOOGLE
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# KONFIGURASI THREADS
THREADS_CLIENT_ID = os.environ.get("THREADS_CLIENT_ID")
THREADS_CLIENT_SECRET = os.environ.get("THREADS_CLIENT_SECRET")

# KONFIGURASI TWITTER
TWITTER_CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET")

# ==========================================
# KONFIGURASI MIDTRANS (PRODUCTION)
# ==========================================
MIDTRANS_API_URL = "https://app.midtrans.com/snap/v1/transactions"
MIDTRANS_SERVER_KEY = os.environ.get("MIDTRANS_SERVER_KEY", "Mid-server-zF-SefFUBo7r1t-qcRPzdBEr_DUMMY")

SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "trendoraautomation@gmail.com") 
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

#GEMINI API KEY
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

user_2fa_store = {}