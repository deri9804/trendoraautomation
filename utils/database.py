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
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                for idx in range(len(all_values)-1, 0, -1):
                    row = all_values[idx]
                    if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                        return {
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
            return None
        except Exception as e:
            print(f"[GSheet Read Error]: {e}")
            return None
            
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
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            found_idx = -1
            
            # Cari apakah email user sudah terdaftar di sheet
            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                    found_idx = idx + 1
                    break
                    
            if found_idx != -1:
                # Update data user yang sudah ada (Kolom A s/d F)
                sheet.update_cell(found_idx, 1, clean_email)
                sheet.update_cell(found_idx, 2, secret)
                sheet.update_cell(found_idx, 3, str(is_linked))
                if name: sheet.update_cell(found_idx, 4, name)
                if api_key: sheet.update_cell(found_idx, 5, api_key)
                if status: sheet.update_cell(found_idx, 6, status)
            else:
                # Cari baris kosong nyata pertama (Mulai dari Baris 2)
                target_row = None
                if len(all_values) > 1:
                    for idx in range(1, len(all_values)):
                        row = all_values[idx]
                        if not row or len(row) == 0 or not str(row[0]).strip():
                            target_row = idx + 1 # 1-based index di Google Sheets
                            break
                            
                if not target_row:
                    target_row = len(all_values) + 1 if len(all_values) > 0 else 2

                row_data = [clean_email, secret, str(is_linked), name, api_key, status]
                # CRITICAL FIX: Tulis tepat dari Kolom A ke F pada target_row
                sheet.update(f"A{target_row}:F{target_row}", [row_data])
                
            print(f"[GSheet Write Success]: Data user {clean_email} berhasil disimpan di Baris {target_row if found_idx == -1 else found_idx} Kolom A!")
            return True
        except Exception as e:
            print(f"[GSheet Write Error]: {e}")
            return False
            
    print(f"[GSheet Write Fallback]: Gagal terhubung ke GSheets, menyimpan sementara ke RAM untuk {clean_email}")
    config.user_2fa_store[clean_email] = {
        'secret': secret, 'is_linked': is_linked, 'name': name, 'api_key': api_key, 'status': status
    }
    return False

def db_get_tiktok_tokens_by_api_key(api_key, email=None):
    """Mencari TikTok tokens dari baris data terbaru dengan prioritas API Key dan fallback ke Email."""
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
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
            all_values = sheet.get_all_values()
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
            all_values = sheet.get_all_values()
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
            all_values = sheet.get_all_values()
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
            all_values = sheet.get_all_values()
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
            all_values = sheet.get_all_values()
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
            all_values = sheet.get_all_values()
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
            accounts.append({
                "id": target_row[7].strip() if len(target_row) > 7 and target_row[7].strip() else "tiktok_primary",
                "platform": "tiktok",
                "name": "TikTok Creator",
                "username": "@creator.tiktok",
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
            all_values = sheet.get_all_values()
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

    # Simpan kembali ke kolom 16
    json_str = json.dumps(existing_accounts, ensure_ascii=False)
    
    if sheet and target_row_idx:
        try:
            sheet.update_cell(target_row_idx, 16, json_str)
            
            # Sync juga ke kolom legacy untuk primary/latest account per platform
            token = account_dict.get('access_token', '')
            if platform == 'tiktok':
                if token: sheet.update_cell(target_row_idx, 7, token)
                if account_dict.get('open_id'): sheet.update_cell(target_row_idx, 8, account_dict.get('open_id'))
                if account_dict.get('refresh_token'): sheet.update_cell(target_row_idx, 9, account_dict.get('refresh_token'))
            elif platform in ['facebook', 'instagram', 'meta']:
                if token: sheet.update_cell(target_row_idx, 10, token)
            elif platform == 'linkedin':
                if token: sheet.update_cell(target_row_idx, 11, token)
            elif platform == 'youtube':
                if token: sheet.update_cell(target_row_idx, 12, token)
                if account_dict.get('refresh_token'): sheet.update_cell(target_row_idx, 13, account_dict.get('refresh_token'))
            elif platform == 'threads':
                if token: sheet.update_cell(target_row_idx, 14, token)
            elif platform in ['twitter', 'x']:
                if token: sheet.update_cell(target_row_idx, 15, token)
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
            all_values = sheet.get_all_values()
            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                    target_row_idx = idx + 1
                    break
            
            if target_row_idx:
                json_str = json.dumps(updated, ensure_ascii=False)
                sheet.update_cell(target_row_idx, 16, json_str)

                # Jika tidak ada lagi akun untuk platform ini, bersihkan kolom legacy
                remaining_for_plat = [a for a in updated if str(a.get('platform')).lower() == p_lower]
                if not remaining_for_plat:
                    if p_lower == 'tiktok':
                        sheet.update_cell(target_row_idx, 7, "")
                        sheet.update_cell(target_row_idx, 8, "")
                        sheet.update_cell(target_row_idx, 9, "")
                    elif p_lower in ['facebook', 'instagram', 'meta']:
                        sheet.update_cell(target_row_idx, 10, "")
                    elif p_lower == 'linkedin':
                        sheet.update_cell(target_row_idx, 11, "")
                    elif p_lower == 'youtube':
                        sheet.update_cell(target_row_idx, 12, "")
                        sheet.update_cell(target_row_idx, 13, "")
                    elif p_lower == 'threads':
                        sheet.update_cell(target_row_idx, 14, "")
                    elif p_lower in ['twitter', 'x']:
                        sheet.update_cell(target_row_idx, 15, "")
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
