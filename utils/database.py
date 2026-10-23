from datetime import datetime
import os
import json
import uuid
import sys

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import config

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False


import time

# IN-MEMORY ANTI-RATE-LIMIT CACHE
# Menyimpan cache hasil get_all_values() selama 15 detik untuk mencegah Google Sheets 429 Rate Limit
_SHEET_CACHE = {
    'values': None,
    'timestamp': 0,
    'ttl': 15
}

# USER PERSISTENT IN-MEMORY CACHE
# Mencegah user otomatis ter-logout saat Google Sheets API mengalami lonjakan request / rate-limit
_USER_CACHE = {}

def invalidate_sheet_cache():
    """Mengosongkan cache setelah operasi tulis/update data."""
    _SHEET_CACHE['timestamp'] = 0

def get_all_sheet_values(sheet=None, force_refresh=False):
    """
    Mengambil data sheet dengan cache in-memory 15 detik.
    Mencegah Google Sheets API terkena rate limit 429 (Quota Exceeded)
    saat user melakukan banyak aksi berturut-turut.
    """
    now = time.time()
    if not force_refresh and _SHEET_CACHE['values'] is not None and (now - _SHEET_CACHE['timestamp']) < _SHEET_CACHE['ttl']:
        return _SHEET_CACHE['values']
    
    if sheet is None:
        sheet = get_gsheet()
    if not sheet:
        return _SHEET_CACHE['values'] or []
    
    try:
        vals = sheet.get_all_values()
        if vals:
            _SHEET_CACHE['values'] = vals
            _SHEET_CACHE['timestamp'] = now
            # Pre-warm user cache
            for idx in range(len(vals)-1, 0, -1):
                row = vals[idx]
                if len(row) > 0 and str(row[0]).strip():
                    u_email = str(row[0]).strip().lower()
                    if u_email not in _USER_CACHE or (idx + 1) >= _USER_CACHE[u_email].get('row_idx', 0):
                        _USER_CACHE[u_email] = {
                            'email': u_email,
                            'secret': str(row[1]).strip() if len(row) > 1 else '',
                            'is_linked': str(row[2]).strip().lower() == 'true' if len(row) > 2 else False,
                            'name': str(row[3]).strip() if len(row) > 3 else '',
                            'api_key': str(row[4]).strip() if len(row) > 4 else '',
                            'status': str(row[5]).strip() if len(row) > 5 else '',
                            'tiktok_connected': bool(str(row[6]).strip()) if len(row) > 6 else False,
                            'meta_connected': bool(str(row[9]).strip()) if len(row) > 9 else False,
                            'linkedin_connected': bool(str(row[10]).strip()) if len(row) > 10 else False,
                            'youtube_connected': bool(str(row[11]).strip()) if len(row) > 11 else False,
                            'threads_connected': bool(str(row[13]).strip()) if len(row) > 13 else False,
                            'twitter_connected': bool(str(row[14]).strip()) if len(row) > 14 else False,
                            'row_idx': idx + 1
                        }
        return vals
    except Exception as e:
        print(f"[GSheets Read Cache Warning]: {e}")
        if _SHEET_CACHE['values'] is not None:
            return _SHEET_CACHE['values']
        return []

def get_gsheet():
    """Koneksi ke Google Sheets (Sheet Utama)."""
    if not HAS_GSPREAD:
        print("[GSheets Error]: Library 'gspread' atau 'google-auth' belum terinstall.")
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        env_creds = config.GOOGLE_CREDS_JSON
        
        if env_creds:
            if isinstance(env_creds, str):
                # Bersihkan string JSON dari kemungkinan quotation berlebih atau escaped newlines
                clean_env = env_creds.strip()
                if clean_env.startswith("'") and clean_env.endswith("'"):
                    clean_env = clean_env[1:-1]
                if clean_env.startswith('"') and clean_env.endswith('"'):
                    clean_env = clean_env[1:-1]
                
                try:
                    creds_dict = json.loads(clean_env)
                except json.JSONDecodeError:
                    clean_env = clean_env.replace('\\n', '\n')
                    creds_dict = json.loads(clean_env)
            else:
                creds_dict = env_creds
            
            # CRITICAL FIX: Perbaiki format private_key agar newline \n terbaca dengan benar di Vercel
            if isinstance(creds_dict, dict) and "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            if not os.path.exists(config.SERVICE_ACCOUNT_FILE):
                print(f"[GSheets Error]: File {config.SERVICE_ACCOUNT_FILE} tidak ditemukan dan GOOGLE_APPLICATION_CREDENTIALS_JSON di Vercel belum diisi!")
                return None
            creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=scopes)
            
        client = gspread.authorize(creds)
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID).sheet1
        return sheet
    except Exception as e:
        print(f"[GSheets Connection Error]: {e}")
        return None

def get_logs_sheet():
    """Koneksi ke Google Sheets khusus tab 'Logs'."""
    if not HAS_GSPREAD:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        env_creds = config.GOOGLE_CREDS_JSON
        
        if env_creds:
            if isinstance(env_creds, str):
                clean_env = env_creds.strip()
                if clean_env.startswith("'") and clean_env.endswith("'"): clean_env = clean_env[1:-1]
                if clean_env.startswith('"') and clean_env.endswith('"'): clean_env = clean_env[1:-1]
                try:
                    creds_dict = json.loads(clean_env)
                except json.JSONDecodeError:
                    clean_env = clean_env.replace('\\n', '\n')
                    creds_dict = json.loads(clean_env)
            else:
                creds_dict = env_creds

            if isinstance(creds_dict, dict) and "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            if not os.path.exists(config.SERVICE_ACCOUNT_FILE):
                return None
            creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=scopes)

        client = gspread.authorize(creds)
        doc = client.open_by_key(config.GOOGLE_SHEET_ID)
        
        sheet = None
        worksheets = doc.worksheets()
        for s in worksheets:
            s_title = s.title.lower()
            if "log" in s_title or "aktivitas" in s_title or "aktifitas" in s_title:
                sheet = s
                break
        if not sheet and len(worksheets) > 1:
            sheet = worksheets[1]
        if not sheet:
            sheet = doc.add_worksheet(title="Logs", rows="1000", cols="10")
            sheet.append_row(["Timestamp", "LogID", "APIKey", "Platform", "Status", "Details", "Keterangan", "MediaURL", "Caption", "Hashtag"])
            
        return sheet
    except Exception as e:
        print(f"[GSheets Logs Connection Error]: {e}")
        return None

def db_get_user(email):
    """Ambil data user dari Google Sheets (scan dari BAWAH agar selalu dapat yg terbaru)."""
    if not email:
        return None
    
    clean_email = str(email).strip().lower()
        
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            if len(all_values) > 1:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                        user_info = {
                            'email': str(row[0]).strip().lower(),
                            'secret': str(row[1]).strip() if len(row) > 1 else '',
                            'is_linked': str(row[2]).strip().lower() == 'true' if len(row) > 2 else False,
                            'name': str(row[3]).strip() if len(row) > 3 else '',
                            'api_key': str(row[4]).strip() if len(row) > 4 else '',
                            'status': str(row[5]).strip() if len(row) > 5 else '',
                            'tiktok_connected': bool(str(row[6]).strip()) if len(row) > 6 else False,
                            'meta_connected': bool(str(row[9]).strip()) if len(row) > 9 else False,
                            'linkedin_connected': bool(str(row[10]).strip()) if len(row) > 10 else False,
                            'youtube_connected': bool(str(row[11]).strip()) if len(row) > 11 else False,
                            'threads_connected': bool(str(row[13]).strip()) if len(row) > 13 else False,
                            'twitter_connected': bool(str(row[14]).strip()) if len(row) > 14 else False,
                            'row_idx': idx + 1  
                        }
                        _USER_CACHE[clean_email] = user_info
                        if clean_email in config.user_2fa_store:
                            config.user_2fa_store[clean_email].update(user_info)
                        return user_info
        except Exception as e:
            print(f"[GSheet Read Error]: {e}")
            
    # Fallback ke memory cache jika sheet sedang rate-limit (429) atau offline
    if clean_email in _USER_CACHE:
        return _USER_CACHE[clean_email]

    if clean_email in config.user_2fa_store:
        user_data = config.user_2fa_store[clean_email]
        user_data['tiktok_connected'] = user_data.get('tiktok_connected', False)
        return user_data
    return None

def db_save_user(email, secret, is_linked, name="", api_key="", status=""):
    """Simpan atau perbarui data user ke Google Sheets."""
    if not email:
        return False
    clean_email = str(email).strip().lower()

    # Simpan ke memori dulu agar sesi tidak hilang
    user_mem = {
        'email': clean_email, 'secret': secret, 'is_linked': is_linked, 'name': name, 'api_key': api_key, 'status': status
    }
    _USER_CACHE[clean_email] = user_mem
    if clean_email in config.user_2fa_store:
        config.user_2fa_store[clean_email].update(user_mem)
    else:
        config.user_2fa_store[clean_email] = user_mem

    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            found_idx = -1
            
            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                    found_idx = idx + 1
                    break
                    
            row_data = [clean_email, secret, str(is_linked), name, api_key, status]
            if found_idx != -1:
                # Update baris dalam 1 batch call (Anti 429)
                sheet.update(f"A{found_idx}:F{found_idx}", [row_data])
            else:
                target_row = None
                if len(all_values) > 1:
                    for idx in range(1, len(all_values)):
                        row = all_values[idx]
                        if not row or len(row) == 0 or not str(row[0]).strip():
                            target_row = idx + 1
                            break
                            
                if not target_row:
                    target_row = len(all_values) + 1 if len(all_values) > 0 else 2

                sheet.update(f"A{target_row}:F{target_row}", [row_data])
                
            invalidate_sheet_cache()
            return True
        except Exception as e:
            print(f"[GSheet Write Error]: {e}")
            return True # Tetap return True karena sudah tersimpan di RAM cache
            
    return True

def db_get_tiktok_tokens_by_api_key(api_key, email=None):
    """Mencari TikTok tokens dari baris data terbaru dengan prioritas API Key dan fallback ke Email."""
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            # 1. Cari berdasarkan API Key (dari baris paling bawah/terbaru)
            if api_key:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 5 and str(row[4]).strip() == api_key:
                        token = str(row[6]).strip() if len(row) >= 7 and str(row[6]).strip() else None
                        if token:
                            return {
                                'access_token': token,
                                'open_id': str(row[7]).strip() if len(row) >= 8 else None,
                                'refresh_token': str(row[8]).strip() if len(row) >= 9 else None,
                                'email': str(row[0]).strip() if len(row) >= 1 else None,
                                'row_idx': idx + 1
                            }

            # 2. Fallback: Cari berdasarkan Email jika token di baris API Key belum terisi
            if email:
                clean_email = str(email).strip().lower()
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 1 and str(row[0]).strip().lower() == clean_email:
                        token = str(row[6]).strip() if len(row) >= 7 and str(row[6]).strip() else None
                        if token:
                            return {
                                'access_token': token,
                                'open_id': str(row[7]).strip() if len(row) >= 8 else None,
                                'refresh_token': str(row[8]).strip() if len(row) >= 9 else None,
                                'email': str(row[0]).strip() if len(row) >= 1 else None,
                                'row_idx': idx + 1
                            }
        except Exception as e:
            print(f"[GSheet Get TikTok Tokens Error]: {e}")
    return {}

def db_get_meta_token_by_api_key(api_key, email=None):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            if api_key:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 5 and str(row[4]).strip() == api_key:
                        token = str(row[9]).strip() if len(row) >= 10 and str(row[9]).strip() else None
                        if token: return token
            if email:
                clean_email = str(email).strip().lower()
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 1 and str(row[0]).strip().lower() == clean_email:
                        token = str(row[9]).strip() if len(row) >= 10 and str(row[9]).strip() else None
                        if token: return token
        except Exception as e:
            print(f"[GSheet Get Meta Token Error]: {e}")
    return None

def db_get_linkedin_token_by_api_key(api_key, email=None):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            if api_key:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 5 and str(row[4]).strip() == api_key:
                        token = str(row[10]).strip() if len(row) >= 11 and str(row[10]).strip() else None
                        if token: return token
            if email:
                clean_email = str(email).strip().lower()
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 1 and str(row[0]).strip().lower() == clean_email:
                        token = str(row[10]).strip() if len(row) >= 11 and str(row[10]).strip() else None
                        if token: return token
        except Exception as e:
            print(f"[GSheet Get LinkedIn Token Error]: {e}")
    return None

def db_get_youtube_tokens_by_api_key(api_key, email=None):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            if api_key:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 5 and str(row[4]).strip() == api_key:
                        access_token = str(row[11]).strip() if len(row) >= 12 and str(row[11]).strip() else None
                        refresh_token = str(row[12]).strip() if len(row) >= 13 and str(row[12]).strip() else None
                        if access_token or refresh_token:
                            return {
                                'access_token': access_token,
                                'refresh_token': refresh_token,
                                'row_idx': idx + 1
                            }
            if email:
                clean_email = str(email).strip().lower()
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 1 and str(row[0]).strip().lower() == clean_email:
                        access_token = str(row[11]).strip() if len(row) >= 12 and str(row[11]).strip() else None
                        refresh_token = str(row[12]).strip() if len(row) >= 13 and str(row[12]).strip() else None
                        if access_token or refresh_token:
                            return {
                                'access_token': access_token,
                                'refresh_token': refresh_token,
                                'row_idx': idx + 1
                            }
        except Exception as e:
            print(f"[GSheet Get YouTube Token Error]: {e}")
    return {}

def db_get_threads_token_by_api_key(api_key, email=None):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            if api_key:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 5 and str(row[4]).strip() == api_key:
                        return row[13] if len(row) >= 14 and row[13].strip() else None
            if email:
                clean_email = str(email).strip().lower()
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 1 and str(row[0]).strip().lower() == clean_email:
                        return row[13] if len(row) >= 14 and row[13].strip() else None
        except Exception as e:
            print(f"[GSheet Get Threads Token Error]: {e}")
    return None

def db_get_twitter_token_by_api_key(api_key, email=None):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            if api_key:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 5 and str(row[4]).strip() == api_key:
                        return row[14] if len(row) >= 15 and row[14].strip() else None
            if email:
                clean_email = str(email).strip().lower()
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) >= 1 and str(row[0]).strip().lower() == clean_email:
                        return row[14] if len(row) >= 15 and row[14].strip() else None
        except Exception as e:
            print(f"[GSheet Get Twitter Token Error]: {e}")
    return None

# =========================================================================
# MULTI-ACCOUNT SOCIAL MEDIA STORAGE & REGISTRY (ALL PLATFORMS)
# Mendukung 20-40+ Akun per User (TikTok, Meta FB, IG, YouTube, X, dll)
# =========================================================================

PLAN_MAX_ACCOUNTS = {
    'starter': 20,
    'creator': 40,
    'agency': 100,
    'trial': 20
}

def db_get_social_accounts(email=None, api_key=None):
    """
    Mengambil seluruh daftar akun medsos yang terhubung untuk user ini dari Kolom 16 (SocialAccountsJSON).
    Jika Kolom 16 belum ada isinya, fungsi ini akan otomatis mendeteksi dan memigrasikan akun lama
    dari kolom legacy (TikTok: col 7-9, Meta: col 10, LinkedIn: col 11, YouTube: col 12-13,
    Threads: col 14, Twitter: col 15).
    """
    clean_email = str(email).strip().lower() if email else None
    sheet = get_gsheet()
    accounts = []
    target_row = None

    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            if len(all_values) > 1:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    match = False
                    if api_key and len(row) >= 5 and str(row[4]).strip() == api_key:
                        match = True
                    elif clean_email and len(row) >= 1 and str(row[0]).strip().lower() == clean_email:
                        match = True
                    
                    if match:
                        target_row = row
                        break
        except Exception as e:
            print(f"[GSheet Read Multi-Account Error]: {e}")

    # Cek dari JSON kolom 16 jika ditemukan di GSheet
    if target_row and len(target_row) >= 16 and target_row[15].strip():
        try:
            parsed = json.loads(target_row[15].strip())
            if isinstance(parsed, list):
                accounts = parsed
        except Exception as e:
            print(f"[GSheet Parse Social Accounts JSON Error]: {e}")

    # Fallback ke in-memory store jika accounts masih kosong
    if not accounts and clean_email and clean_email in config.user_2fa_store:
        accounts = config.user_2fa_store[clean_email].get('social_accounts', [])

    # Jika masih kosong, sintesis dari kolom legacy agar akun lama yang sudah terhubung tidak hilang
    if not accounts and target_row:
        # TikTok (cols 6,7,8)
        if len(target_row) > 6 and target_row[6].strip():
            fallback_name = clean_email.split('@')[0].capitalize() if clean_email else "Akun TikTok"
            fallback_user = f"@{clean_email.split('@')[0]}" if clean_email else "@tiktok_user"
            accounts.append({
                "id": target_row[7].strip() if len(target_row) > 7 and target_row[7].strip() else "tiktok_primary",
                "platform": "tiktok",
                "name": fallback_name,
                "username": fallback_user,
                "avatar_url": "",
                "access_token": target_row[6].strip(),
                "refresh_token": target_row[8].strip() if len(target_row) > 8 else "",
                "open_id": target_row[7].strip() if len(target_row) > 7 else ""
            })
        # Meta Facebook (col 9)
        if len(target_row) > 9 and target_row[9].strip():
            accounts.append({
                "id": "meta_primary",
                "platform": "facebook",
                "name": "Facebook Page Terhubung",
                "username": "facebook.page",
                "avatar_url": "",
                "access_token": target_row[9].strip()
            })
        # LinkedIn (col 10)
        if len(target_row) > 10 and target_row[10].strip():
            accounts.append({
                "id": "linkedin_primary",
                "platform": "linkedin",
                "name": "LinkedIn Profile",
                "username": "linkedin.user",
                "avatar_url": "",
                "access_token": target_row[10].strip()
            })
        # YouTube (cols 11,12)
        if len(target_row) > 11 and target_row[11].strip():
            accounts.append({
                "id": "youtube_primary",
                "platform": "youtube",
                "name": "YouTube Channel Terhubung",
                "username": "@YouTubeChannel",
                "avatar_url": "",
                "access_token": target_row[11].strip(),
                "refresh_token": target_row[12].strip() if len(target_row) > 12 else ""
            })
        # Threads (col 13)
        if len(target_row) > 13 and target_row[13].strip():
            accounts.append({
                "id": "threads_primary",
                "platform": "threads",
                "name": "Threads Profile",
                "username": "threads.user",
                "avatar_url": "",
                "access_token": target_row[13].strip()
            })
        # Twitter (col 14)
        if len(target_row) > 14 and target_row[14].strip():
            accounts.append({
                "id": "twitter_primary",
                "platform": "twitter",
                "name": "Twitter / X Profile",
                "username": "@twitter_user",
                "avatar_url": "",
                "access_token": target_row[14].strip()
            })

    # Singkirkan placeholder meta_primary jika akun Facebook riil sudah ada
    has_real_fb = any(str(a.get('platform', '')).lower() in ['facebook', 'fb', 'facebook_page'] and str(a.get('id', '')) != 'meta_primary' for a in accounts)
    if has_real_fb:
        accounts = [a for a in accounts if not (str(a.get('platform', '')).lower() in ['facebook', 'fb', 'facebook_page'] and str(a.get('id', '')) == 'meta_primary')]

    return accounts

def db_save_social_account(email, account_dict):
    """
    Menyimpan atau memperbarui akun medsos spesifik untuk user ke multi-account registry.
    Mencegah duplikasi dengan mengecek ID dan platform yang sama.
    Juga menyinkronkan token utama ke kolom legacy untuk backward compatibility.
    """
    if not email or not account_dict or not account_dict.get('platform'):
        return False, "Data akun tidak lengkap."

    clean_email = str(email).strip().lower()
    platform = str(account_dict.get('platform')).strip().lower()
    acc_id = str(account_dict.get('id') or f"{platform}_{uuid.uuid4().hex[:8]}").strip()
    account_dict['id'] = acc_id
    account_dict['platform'] = platform

    sheet = get_gsheet()
    target_row_idx = None
    all_values = []
    current_status = ""

    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            # Pastikan header kolom 16 tersedia
            if len(all_values) > 0 and len(all_values[0]) < 16:
                try:
                    sheet.update_cell(1, 16, "SocialAccountsJSON")
                except Exception:
                    pass

            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                    target_row_idx = idx + 1
                    current_status = str(row[5]).strip() if len(row) > 5 else ""
                    break
        except Exception as e:
            print(f"[GSheet Find Row Error]: {e}")

    # Tentukan limit akun berdasarkan paket user
    plan_limit = 20
    status_lower = current_status.lower()
    if 'creator' in status_lower:
        plan_limit = 40
    elif 'agency' in status_lower:
        plan_limit = 100
    else:
        plan_limit = 20

    # Ambil list akun eksisting
    existing_accounts = db_get_social_accounts(email=clean_email)
    
    # Cek apakah akun dengan id dan platform ini sudah ada (update)
    found_idx = -1
    for i, a in enumerate(existing_accounts):
        if str(a.get('platform')).lower() == platform and str(a.get('id')) == acc_id:
            found_idx = i
            break
        # Jika belum ada ID yang cocok, cek kesamaan username jika ada
        elif str(a.get('platform')).lower() == platform and account_dict.get('username') and a.get('username') == account_dict.get('username'):
            found_idx = i
            break

    if found_idx >= 0:
        # Update existing
        existing_accounts[found_idx].update(account_dict)
    else:
        # Check quota limit
        if len(existing_accounts) >= plan_limit:
            return False, f"Batas kuota akun ({plan_limit} akun) untuk paket Anda telah tercapai! Silakan upgrade paket untuk menambah akun lebih banyak."
        existing_accounts.append(account_dict)

    # Singkirkan placeholder meta_primary jika akun Facebook riil sudah ada
    has_real_fb = any(str(a.get('platform', '')).lower() in ['facebook', 'fb', 'facebook_page'] and str(a.get('id', '')) != 'meta_primary' for a in existing_accounts)
    if has_real_fb:
        existing_accounts = [a for a in existing_accounts if not (str(a.get('platform', '')).lower() in ['facebook', 'fb', 'facebook_page'] and str(a.get('id', '')) == 'meta_primary')]

    # Simpan kembali ke kolom 16
    json_str = json.dumps(existing_accounts, ensure_ascii=False)
    
    if sheet and target_row_idx:
        try:
            batch_updates = [
                {'range': f'P{target_row_idx}', 'values': [[json_str]]}
            ]
            
            # Sync juga ke kolom legacy untuk primary/latest account per platform
            token = account_dict.get('access_token', '')
            if platform == 'tiktok':
                op_id = account_dict.get('open_id', '')
                ref_tok = account_dict.get('refresh_token', '')
                batch_updates.append({'range': f'G{target_row_idx}:I{target_row_idx}', 'values': [[token, op_id, ref_tok]]})
            elif platform in ['facebook', 'instagram', 'meta']:
                if token: batch_updates.append({'range': f'J{target_row_idx}', 'values': [[token]]})
            elif platform == 'linkedin':
                if token: batch_updates.append({'range': f'K{target_row_idx}', 'values': [[token]]})
            elif platform == 'youtube':
                ref_tok = account_dict.get('refresh_token', '')
                batch_updates.append({'range': f'L{target_row_idx}:M{target_row_idx}', 'values': [[token, ref_tok]]})
            elif platform == 'threads':
                if token: batch_updates.append({'range': f'N{target_row_idx}', 'values': [[token]]})
            elif platform in ['twitter', 'x']:
                if token: batch_updates.append({'range': f'O{target_row_idx}', 'values': [[token]]})

            sheet.batch_update(batch_updates)
            invalidate_sheet_cache()
        except Exception as e:
            print(f"[GSheet Save Social Account Error]: {e}")

    # Sync ke memory store
    if clean_email in config.user_2fa_store:
        config.user_2fa_store[clean_email]['social_accounts'] = existing_accounts

    return True, existing_accounts

def db_delete_social_account(email, platform, account_id):
    """
    Menghapus akun medsos tertentu berdasarkan platform dan account_id.
    Jika semua akun platform tersebut dihapus, kolom legacy juga dibersihkan.
    Menggunakan batch_update (1 request) untuk mencegah rate-limit Google Sheets.
    """
    if not email:
        return False, "Email wajib disertakan."

    clean_email = str(email).strip().lower()
    p_lower = str(platform).strip().lower() if platform else ''
    acc_id = str(account_id).strip()

    existing = db_get_social_accounts(email=clean_email)
    updated = [a for a in existing if not (str(a.get('platform')).lower() == p_lower and str(a.get('id')) == acc_id)]

    sheet = get_gsheet()
    target_row_idx = None
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                    target_row_idx = idx + 1
                    break
            
            if target_row_idx:
                json_str = json.dumps(updated, ensure_ascii=False)
                remaining_for_plat = [a for a in updated if str(a.get('platform')).lower() == p_lower]
                
                # Single batch update (Hanya 1 HTTP Request ke GSheets!)
                batch_updates = [
                    {'range': f'P{target_row_idx}', 'values': [[json_str]]}
                ]
                if not remaining_for_plat:
                    if p_lower == 'tiktok':
                        batch_updates.append({'range': f'G{target_row_idx}:I{target_row_idx}', 'values': [["", "", ""]]})
                    elif p_lower in ['facebook', 'instagram', 'meta']:
                        batch_updates.append({'range': f'J{target_row_idx}', 'values': [[""]]})
                    elif p_lower == 'linkedin':
                        batch_updates.append({'range': f'K{target_row_idx}', 'values': [[""]]})
                    elif p_lower == 'youtube':
                        batch_updates.append({'range': f'L{target_row_idx}:M{target_row_idx}', 'values': [["", ""]]})
                    elif p_lower == 'threads':
                        batch_updates.append({'range': f'N{target_row_idx}', 'values': [[""]]})
                    elif p_lower in ['twitter', 'x']:
                        batch_updates.append({'range': f'O{target_row_idx}', 'values': [[""]]})
                
                sheet.batch_update(batch_updates)
                invalidate_sheet_cache()
        except Exception as e:
            print(f"[GSheet Delete Social Account Error]: {e}")

    if clean_email in config.user_2fa_store:
        config.user_2fa_store[clean_email]['social_accounts'] = updated

    return True, updated

def db_get_social_account_token(email=None, api_key=None, platform=None, account_id=None):
    """
    Mengambil token akun spesifik (berdasarkan account_id).
    Jika account_id tidak diberikan, mengambil akun pertama yang cocok dengan platform.
    Jika tidak ada di daftar multi-account, fallback ke fungsi legacy.
    """
    accounts = db_get_social_accounts(email=email, api_key=api_key)
    p_lower = str(platform).strip().lower() if platform else ''
    
    if account_id:
        for a in accounts:
            if str(a.get('platform')).lower() == p_lower and str(a.get('id')) == str(account_id):
                return a
    
    # Fallback akun pertama dari platform
    for a in accounts:
        if str(a.get('platform')).lower() == p_lower:
            return a

    return None

# =========================================================================
# SCHEDULED POSTS & CONTENT CALENDAR DATABASE ENGINE
# =========================================================================

def get_scheduled_sheet():
    """Koneksi ke Google Sheets khusus tab 'ScheduledPosts'."""
    if not HAS_GSPREAD:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        env_creds = config.GOOGLE_CREDS_JSON
        
        if env_creds:
            if isinstance(env_creds, str):
                clean_env = env_creds.strip()
                if clean_env.startswith("'") and clean_env.endswith("'"): clean_env = clean_env[1:-1]
                if clean_env.startswith('"') and clean_env.endswith('"'): clean_env = clean_env[1:-1]
                try:
                    creds_dict = json.loads(clean_env)
                except json.JSONDecodeError:
                    clean_env = clean_env.replace('\\n', '\n')
                    creds_dict = json.loads(clean_env)
            else:
                creds_dict = env_creds

            if isinstance(creds_dict, dict) and "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            if not os.path.exists(config.SERVICE_ACCOUNT_FILE):
                return None
            creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=scopes)

        client = gspread.authorize(creds)
        doc = client.open_by_key(config.GOOGLE_SHEET_ID)
        
        sheet = None
        worksheets = doc.worksheets()
        for s in worksheets:
            s_title = s.title.lower()
            if "schedule" in s_title or "jadwal" in s_title or "kalender" in s_title:
                sheet = s
                break
        if not sheet:
            sheet = doc.add_worksheet(title="ScheduledPosts", rows="2000", cols="12")
            sheet.append_row([
                "ID", "UserEmail", "Platform", "AccountID", "AccountName",
                "VideoURL", "Title", "Caption", "ScheduledAt", "Status",
                "PublishID", "CreatedAt"
            ])
            
        return sheet
    except Exception as e:
        print(f"[GSheets ScheduledPosts Connection Error]: {e}")
        return None

# In-memory store fallback for scheduled posts
SCHEDULED_POSTS_CACHE = []

def db_save_scheduled_post(post_dict):
    """Menyimpan jadwal postingan baru ke Google Sheets & Cache lokal."""
    if not post_dict:
        return False, "Data jadwal kosong."
    
    post_id = str(post_dict.get('id') or f"sched_{uuid.uuid4().hex[:10]}")
    post_dict['id'] = post_id
    post_dict['status'] = post_dict.get('status', 'PENDING')
    now_str = datetime.now().isoformat()
    post_dict['created_at'] = post_dict.get('created_at', now_str)

    row_data = [
        post_id,
        str(post_dict.get('user_email', '')).strip().lower(),
        str(post_dict.get('platform', 'facebook')).lower(),
        str(post_dict.get('account_id', '')),
        str(post_dict.get('account_name', '')),
        str(post_dict.get('video_url', '')),
        str(post_dict.get('title', '')),
        str(post_dict.get('caption', '')),
        str(post_dict.get('scheduled_at', '')),
        post_dict['status'],
        str(post_dict.get('publish_id', '')),
        post_dict['created_at']
    ]

    sheet = get_scheduled_sheet()
    if sheet:
        try:
            sheet.append_row(row_data)
        except Exception as e:
            print(f"[GSheet Save Scheduled Post Error]: {e}")

    # Simpan ke cache memory
    existing_idx = next((i for i, p in enumerate(SCHEDULED_POSTS_CACHE) if p.get('id') == post_id), -1)
    if existing_idx >= 0:
        SCHEDULED_POSTS_CACHE[existing_idx] = post_dict
    else:
        SCHEDULED_POSTS_CACHE.append(post_dict)

    return True, post_dict

def db_get_scheduled_posts(email=None, status=None):
    """Mengambil daftar postingan terjadwal untuk user (atau semua jika email=None)."""
    clean_email = str(email).strip().lower() if email else None
    results = []

    sheet = get_scheduled_sheet()
    if sheet:
        try:
            all_rows = sheet.get_all_values()
            if len(all_rows) > 1:
                for idx, row in enumerate(all_rows[1:], start=2):
                    if len(row) >= 10:
                        p_email = str(row[1]).strip().lower()
                        p_status = str(row[9]).strip().upper()
                        
                        if clean_email and p_email != clean_email:
                            continue
                        if status and p_status != str(status).strip().upper():
                            continue

                        results.append({
                            "id": str(row[0]).strip(),
                            "user_email": p_email,
                            "platform": str(row[2]).strip().lower(),
                            "account_id": str(row[3]).strip() if len(row) > 3 else "",
                            "account_name": str(row[4]).strip() if len(row) > 4 else "",
                            "video_url": str(row[5]).strip() if len(row) > 5 else "",
                            "title": str(row[6]).strip() if len(row) > 6 else "",
                            "caption": str(row[7]).strip() if len(row) > 7 else "",
                            "scheduled_at": str(row[8]).strip() if len(row) > 8 else "",
                            "status": p_status,
                            "publish_id": str(row[10]).strip() if len(row) > 10 else "",
                            "created_at": str(row[11]).strip() if len(row) > 11 else "",
                            "row_idx": idx
                        })
        except Exception as e:
            print(f"[GSheet Get Scheduled Posts Error]: {e}")

    # Jika sheet kosong/gagal, ambil dari cache
    if not results and SCHEDULED_POSTS_CACHE:
        for p in SCHEDULED_POSTS_CACHE:
            p_email = str(p.get('user_email', '')).lower()
            p_status = str(p.get('status', '')).upper()
            if clean_email and p_email != clean_email:
                continue
            if status and p_status != str(status).upper():
                continue
            results.append(p)

    # Urutkan berdasarkan waktu scheduled_at
    results.sort(key=lambda x: x.get('scheduled_at', ''), reverse=False)
    return results

def db_update_scheduled_post(post_id, updates_dict):
    """Memperbarui status atau data postingan terjadwal (misal dari PENDING ke PUBLISHED)."""
    if not post_id or not updates_dict:
        return False
    
    sheet = get_scheduled_sheet()
    if sheet:
        try:
            all_rows = sheet.get_all_values()
            for idx, row in enumerate(all_rows[1:], start=2):
                if len(row) >= 1 and str(row[0]).strip() == str(post_id).strip():
                    if 'status' in updates_dict:
                        sheet.update_cell(idx, 10, str(updates_dict['status']).upper())
                    if 'publish_id' in updates_dict:
                        sheet.update_cell(idx, 11, str(updates_dict['publish_id']))
                    break
        except Exception as e:
            print(f"[GSheet Update Scheduled Post Error]: {e}")

    for p in SCHEDULED_POSTS_CACHE:
        if p.get('id') == post_id:
            p.update(updates_dict)
            break

    return True

def db_delete_scheduled_post(post_id, email=None):
    """Membatalkan jadwal postingan (mengubah status menjadi CANCELLED)."""
    return db_update_scheduled_post(post_id, {"status": "CANCELLED"})


# =========================================================================
# INSTAGRAM COMMENT-TO-DM AUTORESPONDER (MANYCHAT ENGINE)
# =========================================================================

def get_instagram_auto_dm_sheet(sheet_id=None):
    """Koneksi ke Google Sheets khusus tab 'Instagram_Auto_DM'."""
    if not HAS_GSPREAD:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        env_creds = config.GOOGLE_CREDS_JSON
        
        if env_creds:
            if isinstance(env_creds, str):
                clean_env = env_creds.strip()
                if clean_env.startswith("'") and clean_env.endswith("'"): clean_env = clean_env[1:-1]
                if clean_env.startswith('"') and clean_env.endswith('"'): clean_env = clean_env[1:-1]
                try: creds_dict = json.loads(clean_env)
                except json.JSONDecodeError:
                    clean_env = clean_env.replace('\\n', '\n')
                    creds_dict = json.loads(clean_env)
            else: creds_dict = env_creds
            if isinstance(creds_dict, dict) and "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            if not os.path.exists(config.SERVICE_ACCOUNT_FILE): return None
            creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=scopes)

        client = gspread.authorize(creds)
        raw_target = str(sheet_id or config.GOOGLE_SHEET_ID or '').strip()
        if '/d/' in raw_target:
            raw_target = raw_target.split('/d/')[1].split('/')[0].split('?')[0].strip()
        target_id = raw_target or config.GOOGLE_SHEET_ID
        doc = client.open_by_key(target_id)
        
        target_sheet = None
        for s in doc.worksheets():
            if s.title.lower() in ["instagram_auto_dm", "instagramautodm", "ig_auto_dm", "autodm"]:
                target_sheet = s
                break
        if not target_sheet:
            target_sheet = doc.add_worksheet(title="Instagram_Auto_DM", rows="500", cols="8")
            target_sheet.append_row(["Email", "Trigger_Keyword", "Match_Type", "Comment_Reply", "DM_Reply", "Status", "Catatan", "Updated_At"])
        return target_sheet
    except Exception as e:
        print(f"[GSheets IG Auto DM Connection Error]: {e}")
        return None

def db_ensure_ig_auto_dm_worksheet_template(email, sheet_id=None):
    sheet = get_instagram_auto_dm_sheet(sheet_id=sheet_id)
    if not sheet:
        return False, "Gagal menghubungkan ke Google Sheets."
    try:
        rows = sheet.get_all_values()
        clean_email = (email or 'user@trendora.com').strip().lower()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if len(rows) <= 1:
            samples = [
                [clean_email, "MAU", "contains", "Halo kak! Linknya sudah kami kirimkan ke DM kamu ya, cek inbox kamu sekarang 😊✨", "Hai kak! Ini dia link akses yang kamu minta: https://trendoraautomation.my.id 🔥 Jangan lupa follow akun kami ya!", "AKTIF", "Keyword default MAU", now_str],
                [clean_email, "LINK", "contains", "Siap kak, linknya sudah meluncur ke DM kamu! Cek sekarang ya 🙏", "Halo! Terima kasih atas minatnya. Ini link langsungnya: https://trendoraautomation.my.id", "AKTIF", "Keyword default LINK", now_str],
                [clean_email, "INFO", "contains", "Informasi lengkapnya sudah kami DM ya kak, silahkan dicek inboxnya ✨", "Halo kak! Informasi detail & cara pendaftarannya bisa dicek di: https://trendoraautomation.my.id", "AKTIF", "Keyword default INFO", now_str],
                [clean_email, "HARGA", "contains", "Halo kak, rincian harganya sudah kami kirim ke DM ya! 🏷️", "Halo kak! Rincian paket & promo hari ini mulai dari Rp 99.000. Cek katalognya di sini: https://trendoraautomation.my.id", "AKTIF", "Keyword default HARGA", now_str]
            ]
            for row in samples:
                sheet.append_row(row)
        return True, "Tab Instagram_Auto_DM siap digunakan."
    except Exception as e:
        return False, str(e)

def db_get_ig_auto_dm_rules_from_sheet(email, sheet_id=None):
    sheet = get_instagram_auto_dm_sheet(sheet_id=sheet_id)
    if not sheet:
        return []
    try:
        clean_email = (email or '').strip().lower()
        rows = sheet.get_all_values()
        if len(rows) <= 1:
            return []
        
        rules = []
        for idx, r in enumerate(rows[1:], start=2):
            if len(r) < 5:
                continue
            row_email = (r[0] or '').strip().lower()
            if row_email and clean_email and row_email != clean_email:
                continue
            
            kw = (r[1] or '').strip()
            if not kw:
                continue
            
            m_type = (r[2] or 'contains').strip().lower()
            if m_type not in ['exact', 'contains']:
                m_type = 'contains'
                
            comm_reply = (r[3] or '').strip()
            dm_reply = (r[4] or '').strip()
            status_raw = (r[5] or 'AKTIF').strip().upper() if len(r) > 5 else 'AKTIF'
            is_active = status_raw in ['AKTIF', 'ACTIVE', 'TRUE', '1', 'ON']
            notes = (r[6] or '').strip() if len(r) > 6 else ''
            
            rules.append({
                "id": f"sheet_row_{idx}",
                "keyword": kw,
                "match_type": m_type,
                "comment_reply": comm_reply,
                "dm_reply": dm_reply,
                "is_active": is_active,
                "notes": notes,
                "source": "spreadsheet",
                "row_index": idx
            })
        return rules
    except Exception as e:
        print(f"[GSheets Parse IG Rules Error]: {e}")
        return []

def db_get_ig_auto_dm_settings(email):
    clean_email = str(email).strip().lower() if email else None
    if not clean_email:
        return {}

    default_settings = {
        "is_enabled": False,
        "source_mode": "dashboard",
        "sheet_tab": "Instagram_Auto_DM",
        "custom_sheet_id": "",
        "rules": [
            {
                "id": "rule_1",
                "keyword": "MAU",
                "match_type": "contains",
                "comment_reply": "Halo kak! Linknya sudah kami kirimkan ke DM kamu ya, cek inbox kamu sekarang 😊✨",
                "dm_reply": "Hai kak! Ini dia link akses yang kamu minta: https://trendoraautomation.my.id 🔥 Jangan lupa follow akun kami ya!",
                "is_active": True
            },
            {
                "id": "rule_2",
                "keyword": "LINK",
                "match_type": "contains",
                "comment_reply": "Siap kak, linknya sudah meluncur ke DM kamu! Cek sekarang ya 🙏",
                "dm_reply": "Halo! Terima kasih atas minatnya. Ini link langsungnya: https://trendoraautomation.my.id",
                "is_active": True
            }
        ],
        "stats": {
            "total_comments_detected": 0,
            "total_dm_sent": 0,
            "total_replies_sent": 0,
            "last_activity": ""
        }
    }

    if clean_email in config.user_2fa_store and 'ig_auto_dm' in config.user_2fa_store[clean_email]:
        return config.user_2fa_store[clean_email]['ig_auto_dm']

    sheet = get_gsheet()
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                    if len(row) >= 17 and row[16].strip():
                        parsed = json.loads(row[16].strip())
                        if isinstance(parsed, dict):
                            merged = default_settings.copy()
                            merged.update(parsed)
                            if clean_email not in config.user_2fa_store:
                                config.user_2fa_store[clean_email] = {}
                            config.user_2fa_store[clean_email]['ig_auto_dm'] = merged
                            return merged
                    break
        except Exception as e:
            print(f"[GSheet Read IG Auto DM Error]: {e}")

    return default_settings

def db_save_ig_auto_dm_settings(email, settings_dict):
    clean_email = str(email).strip().lower() if email else None
    if not clean_email or not isinstance(settings_dict, dict):
        return False, "Data pengaturan tidak valid."

    sheet = get_gsheet()
    target_row_idx = None
    if sheet:
        try:
            all_values = get_all_sheet_values(sheet)
            if len(all_values) > 0 and len(all_values[0]) < 17:
                try:
                    sheet.update_cell(1, 17, "InstagramAutoDM_JSON")
                except Exception:
                    pass

            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                    target_row_idx = idx + 1
                    break
        except Exception as e:
            print(f"[GSheet Find Row IG Auto DM Error]: {e}")

    if clean_email not in config.user_2fa_store:
        config.user_2fa_store[clean_email] = {}
    config.user_2fa_store[clean_email]['ig_auto_dm'] = settings_dict

    if sheet and target_row_idx:
        try:
            json_str = json.dumps(settings_dict, ensure_ascii=False)
            batch_updates = [
                {'range': f'Q{target_row_idx}', 'values': [[json_str]]}
            ]
            sheet.batch_update(batch_updates)
            invalidate_sheet_cache()
            return True, "Pengaturan Instagram Auto DM berhasil disimpan."
        except Exception as e:
            print(f"[GSheet Save IG Auto DM Error]: {e}")
            return False, str(e)

    return True, "Tersimpan di sesi server."

def db_find_user_by_instagram_id(ig_id):
    clean_id = str(ig_id).strip()
    sheet = get_gsheet()
    if not sheet or not clean_id:
        return None
    try:
        all_values = get_all_sheet_values(sheet)
        for idx in range(len(all_values)-1, 0, -1):
            row = all_values[idx]
            email = str(row[0]).strip().lower() if len(row) > 0 else ""
            if not email:
                continue

            if len(row) >= 16 and row[15].strip():
                try:
                    accs = json.loads(row[15].strip())
                    for a in accs:
                        a_plat = str(a.get('platform', '')).lower()
                        a_id = str(a.get('id', '')).strip()
                        if a_plat in ['instagram', 'facebook'] and (a_id == clean_id or clean_id in a_id):
                            return {
                                "email": email,
                                "access_token": a.get('access_token', ''),
                                "account": a
                            }
                except Exception:
                    pass

            if len(row) >= 10 and row[9].strip():
                return {
                    "email": email,
                    "access_token": row[9].strip(),
                    "account": {"id": clean_id, "platform": "instagram"}
                }
    except Exception as e:
        print(f"[GSheet Find User By IG Error]: {e}")
    return None

def db_record_ig_auto_dm_stat(email, dm_success=True, reply_success=True):
    try:
        settings = db_get_ig_auto_dm_settings(email)
        stats = settings.get('stats', {})
        stats['total_comments_detected'] = stats.get('total_comments_detected', 0) + 1
        if dm_success:
            stats['total_dm_sent'] = stats.get('total_dm_sent', 0) + 1
        if reply_success:
            stats['total_replies_sent'] = stats.get('total_replies_sent', 0) + 1
        stats['last_activity'] = datetime.now().isoformat()
        settings['stats'] = stats
        db_save_ig_auto_dm_settings(email, settings)
    except Exception as e:
        print(f"[Record IG Stat Error]: {e}")

def db_log_ig_auto_dm_event(email, log_info):
    try:
        sheet = get_logs_sheet()
        if sheet:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_id = f"IG_DM_{uuid.uuid4().hex[:8]}"
            details = f"Commenter: @{log_info.get('commenter_username')} | Keyword: {log_info.get('keyword_matched')} | Mode: {log_info.get('source_mode')} | DM: {'OK' if log_info.get('dm_success') else 'FAIL'} | Reply: {'OK' if log_info.get('reply_success') else 'FAIL'}"
            sheet.append_row([
                now_str,
                log_id,
                email,
                "Instagram",
                "SUCCESS" if (log_info.get('dm_success') or log_info.get('reply_success')) else "FAILED",
                details,
                f"Auto DM Comment-to-DM ({log_info.get('source_mode')})",
                "",
                log_info.get('comment_text', '')[:100],
                ""
            ])
    except Exception as e:
        print(f"[Log IG Event Error]: {e}")
