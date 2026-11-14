import os

basedir = os.path.abspath(os.path.dirname(__file__))
env_file = os.path.join(basedir, '.env')

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(env_file, override=True)
except Exception:
    pass

# Manual fallback parser jika python-dotenv belum terpasang
if os.path.exists(env_file):
    try:
        with open(env_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        print("[Config Env Load Error]:", e)

# CONFIGURATION SECRET KEY FOR SESSIONS
SECRET_KEY = os.environ.get("SECRET_KEY", "trendora_session_isolated_secret_key_2026_x89a")

# CONFIGURATION GOOGLE SHEETS
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1P0zTEwtMmWfxhHAY6-QbQd5to6Id1rzazgel-PiSJwI") 
SERVICE_ACCOUNT_FILE = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

# CONFIGURATION TIKTOK DEVELOPER
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY") or os.environ.get("TIKTOK_KEY") or os.environ.get("TIKTOK_APP_ID") or os.environ.get("TIKTOK_CLIENT_ID")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET") or os.environ.get("TIKTOK_SECRET") or os.environ.get("TIKTOK_APP_SECRET")

# CONFIGURATION META (FACEBOOK & INSTAGRAM)
META_CLIENT_ID = os.environ.get("META_CLIENT_ID") or os.environ.get("META_APP_ID") or os.environ.get("FACEBOOK_APP_ID") or os.environ.get("FB_APP_ID") or os.environ.get("FACEBOOK_CLIENT_ID")
META_CLIENT_SECRET = os.environ.get("META_CLIENT_SECRET") or os.environ.get("META_APP_SECRET") or os.environ.get("FACEBOOK_APP_SECRET") or os.environ.get("FB_APP_SECRET") or os.environ.get("FACEBOOK_CLIENT_SECRET")
META_WEBHOOK_VERIFY_TOKEN = os.environ.get("META_WEBHOOK_VERIFY_TOKEN", "trendora_meta_secret_123")

# CONFIGURATION LINKEDIN
LINKEDIN_CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")

# CONFIGURATION YOUTUBE / GOOGLE
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# CONFIGURATION THREADS
THREADS_CLIENT_ID = os.environ.get("THREADS_CLIENT_ID")
THREADS_CLIENT_SECRET = os.environ.get("THREADS_CLIENT_SECRET")

# CONFIGURATION TWITTER
TWITTER_CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET")

# CONFIGURATION MIDTRANS (PRODUCTION)
MIDTRANS_API_URL = "https://app.midtrans.com/snap/v1/transactions"
MIDTRANS_SERVER_KEY = os.environ.get("MIDTRANS_SERVER_KEY", "Mid-server-zF-SefFUBo7r1t-qcRPzdBEr_DUMMY")

# CONFIGURATION SMTP & GEMINI
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "trendoraautomation@gmail.com") 
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# CONFIGURATION LEAD SCRAPER (OPSI A: GOOGLE SEARCH API & SERPER & APIFY)
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
GOOGLE_SEARCH_ENGINE_ID = os.environ.get("GOOGLE_SEARCH_ENGINE_ID", os.environ.get("GOOGLE_CSE_CX", ""))
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")


# In-memory store fallback
user_2fa_store = {}
