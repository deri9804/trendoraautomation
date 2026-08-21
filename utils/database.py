import os
import json
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
            for idx in range(len(all_values)-1, 0, -1):
                row = all_values[idx]
                if len(row) > 0 and str(row[0]).strip().lower() == clean_email:
                    found_idx = idx + 1
                    break
                    
            if found_idx != -1:
                sheet.update_cell(found_idx, 2, secret)
                sheet.update_cell(found_idx, 3, str(is_linked))
                if name: sheet.update_cell(found_idx, 4, name)
                if api_key: sheet.update_cell(found_idx, 5, api_key)
                if status: sheet.update_cell(found_idx, 6, status)
            else:
                sheet.append_row([clean_email, secret, str(is_linked), name, api_key, status])
            print(f"[GSheet Write Success]: Data user {clean_email} berhasil disimpan ke Google Sheets!")
            return True
        except Exception as e:
            print(f"[GSheet Write Error]: {e}")
            return False
            
    print(f"[GSheet Write Fallback]: Gagal terhubung ke GSheets, menyimpan sementara ke RAM untuk {clean_email}")
    config.user_2fa_store[clean_email] = {
        'secret': secret, 'is_linked': is_linked, 'name': name, 'api_key': api_key, 'status': status
    }
    return False

def db_get_tiktok_tokens_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return {
                        'access_token': row[6] if len(row) >= 7 else None,
                        'open_id': row[7] if len(row) >= 8 else None
                    }
        except Exception as e:
            print(f"[GSheet Get Tokens Error]: {e}")
    return {}

def db_get_meta_token_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return row[9] if len(row) >= 10 else None
        except Exception as e:
            print(f"[GSheet Get Meta Token Error]: {e}")
    return None

def db_get_linkedin_token_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return row[10] if len(row) >= 11 else None
        except Exception as e:
            print(f"[GSheet Get LinkedIn Token Error]: {e}")
    return None

def db_get_youtube_tokens_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return {
                        'access_token': row[11] if len(row) >= 12 else None,
                        'refresh_token': row[12] if len(row) >= 13 else None
                    }
        except Exception as e:
            print(f"[GSheet Get YouTube Token Error]: {e}")
    return {}

def db_get_threads_token_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return row[13] if len(row) >= 14 else None
        except Exception as e:
            print(f"[GSheet Get Threads Token Error]: {e}")
    return None

def db_get_twitter_token_by_api_key(api_key):
    sheet = get_gsheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx == 0: continue
                if len(row) >= 5 and row[4].strip() == api_key:
                    return row[14] if len(row) >= 15 else None
        except Exception as e:
            print(f"[GSheet Get Twitter Token Error]: {e}")
    return None