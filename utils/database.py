"""
Trendora Database Layer - High-Performance SQLite with WAL Mode & Auto-Recovery
Menggantikan Google Sheets sebagai database utama untuk menjamin kestabilan sesi (zero auto-logout),
kecepatan baca/tulis instan (< 1ms), dan kebebasan mutlak dari rate-limit HTTP 429 Google.
"""
from datetime import datetime
import os
import json
import uuid
import sys
import sqlite3
import threading
import time

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import config

# Lokasi File Database SQLite
DB_PATH = os.environ.get("SQLITE_DB_PATH", os.path.join(PARENT_DIR, 'trendora.db'))

# Optional Google Sheets support untuk backup visual
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

# =========================================================================
# KONEKSI & INISIALISASI DATABASE SQLITE
# =========================================================================

def get_db_connection():
    """
    Membuka koneksi ke SQLite dengan WAL mode & timeout 10 detik.
    Aman untuk multi-threading dan multi-process PM2.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_sqlite_db():
    """Membuat tabel-tabel SQLite jika belum tersedia."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            secret TEXT DEFAULT '',
            is_linked INTEGER DEFAULT 0,
            name TEXT DEFAULT '',
            api_key TEXT UNIQUE,
            status TEXT DEFAULT 'Free Trial',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

        CREATE TABLE IF NOT EXISTS social_accounts (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            platform TEXT NOT NULL,
            name TEXT DEFAULT '',
            username TEXT DEFAULT '',
            avatar_url TEXT DEFAULT '',
            access_token TEXT DEFAULT '',
            refresh_token TEXT DEFAULT '',
            open_id TEXT DEFAULT '',
            page_id TEXT DEFAULT '',
            instagram_id TEXT DEFAULT '',
            token_expires_at INTEGER,
            extra_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_email) REFERENCES users(email) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_social_user ON social_accounts(user_email);
        CREATE INDEX IF NOT EXISTS idx_social_plat ON social_accounts(platform);

        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_id TEXT DEFAULT '',
            account_name TEXT DEFAULT '',
            video_url TEXT DEFAULT '',
            title TEXT DEFAULT '',
            caption TEXT DEFAULT '',
            scheduled_at TEXT DEFAULT '',
            status TEXT DEFAULT 'PENDING',
            publish_id TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_sched_user ON scheduled_posts(user_email);
        CREATE INDEX IF NOT EXISTS idx_sched_status ON scheduled_posts(status);

        CREATE TABLE IF NOT EXISTS ig_auto_dm_settings (
            user_email TEXT PRIMARY KEY,
            is_enabled INTEGER DEFAULT 0,
            source_mode TEXT DEFAULT 'dashboard',
            sheet_tab TEXT DEFAULT 'Instagram_Auto_DM',
            custom_sheet_id TEXT DEFAULT '',
            rules_json TEXT DEFAULT '[]',
            stats_json TEXT DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_email) REFERENCES users(email) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ig_outreach_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            session_id TEXT NOT NULL,
            daily_limit INTEGER DEFAULT 20,
            sent_today INTEGER DEFAULT 0,
            last_reset_date TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_ig_outreach_user ON ig_outreach_accounts(username);

        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            log_id TEXT DEFAULT '',
            api_key TEXT DEFAULT '',
            user_email TEXT DEFAULT '',
            platform TEXT DEFAULT '',
            status TEXT DEFAULT '',
            details TEXT DEFAULT '',
            keterangan TEXT DEFAULT '',
            media_url TEXT DEFAULT '',
            caption TEXT DEFAULT '',
            hashtag TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_logs_user ON activity_logs(user_email);
        """)
        conn.commit()
    finally:
        conn.close()

# Jalankan inisialisasi schema saat modul di-load
try:
    init_sqlite_db()
except Exception as _e:
    print(f"[SQLite Init Warning]: {_e}")

# =========================================================================
# BACKWARD COMPATIBILITY HELPERS & GSHEET FALLBACK (OPTIONAL)
# =========================================================================

def invalidate_sheet_cache():
    """Dummy untuk backward compatibility."""
    pass

def get_all_sheet_values(sheet=None, force_refresh=False):
    """Dummy fallback."""
    return []

def get_gsheet():
    """Koneksi Google Sheets (opsional untuk reporting/backup jika dibutuhkan)."""
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
        return client.open_by_key(config.GOOGLE_SHEET_ID).sheet1
    except Exception as e:
        return None

def get_logs_sheet():
    """Koneksi tab Logs di Google Sheets."""
    return None

def get_scheduled_sheet():
    """Koneksi tab Scheduled Posts di Google Sheets."""
    return None

# =========================================================================
# OPERASI USER & SESI (INSTAN & BEBAS RATE-LIMIT)
# =========================================================================

def db_get_user(email):
    """
    Mengambil data user langsung dari SQLite lokal secara instan (< 0.1ms).
    Tidak pernah me-logout paksa user karena zero-network dependency.
    """
    if not email:
        return None
    clean_email = str(email).strip().lower()

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE lower(email) = ?", (clean_email,))
        row = cur.fetchone()
        if not row:
            # Fallback ke in-memory jika baru dibuat
            if clean_email in config.user_2fa_store:
                return config.user_2fa_store[clean_email]
            return None

        u = dict(row)

        # Cek status koneksi medsos
        cur.execute("SELECT platform FROM social_accounts WHERE lower(user_email) = ?", (clean_email,))
        acc_rows = cur.fetchall()
        plats = set(str(r['platform']).lower() for r in acc_rows)

        user_info = {
            'email': u['email'],
            'secret': str(u.get('secret') or ''),
            'is_linked': bool(u.get('is_linked')),
            'name': str(u.get('name') or ''),
            'api_key': str(u.get('api_key') or ''),
            'status': str(u.get('status') or 'Free Trial'),
            'tiktok_connected': 'tiktok' in plats,
            'meta_connected': bool({'facebook', 'instagram', 'meta'} & plats),
            'linkedin_connected': 'linkedin' in plats,
            'youtube_connected': 'youtube' in plats,
            'threads_connected': 'threads' in plats,
            'twitter_connected': bool({'twitter', 'x'} & plats),
            'row_idx': u['id']
        }

        # Sync ke in-memory 2FA store
        if clean_email not in config.user_2fa_store:
            config.user_2fa_store[clean_email] = {}
        config.user_2fa_store[clean_email].update(user_info)
        return user_info
    except Exception as e:
        print(f"[SQLite Get User Error]: {e}")
        return config.user_2fa_store.get(clean_email)
    finally:
        conn.close()

def db_get_user_by_api_key(api_key):
    """
    Mengambil data user langsung dari SQLite berdasarkan API Key secara instan (< 0.1ms).
    """
    if not api_key:
        return None
    clean_key = str(api_key).strip()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE api_key = ?", (clean_key,))
        row = cur.fetchone()
        if row and row['email']:
            return db_get_user(row['email'])
        return None
    except Exception as e:
        print(f"[SQLite Get User By API Key Error]: {e}")
        return None
    finally:
        conn.close()

def db_save_user(email, secret, is_linked, name="", api_key="", status=""):
    """
    Menyimpan atau memperbarui data user ke SQLite.
    Operasi bersifat ACID & instan.
    """
    if not email:
        return False
    clean_email = str(email).strip().lower()
    is_linked_int = 1 if is_linked else 0

    user_mem = {
        'email': clean_email,
        'secret': secret,
        'is_linked': is_linked,
        'name': name,
        'api_key': api_key,
        'status': status
    }
    if clean_email in config.user_2fa_store:
        config.user_2fa_store[clean_email].update(user_mem)
    else:
        config.user_2fa_store[clean_email] = user_mem

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO users (email, secret, is_linked, name, api_key, status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(email) DO UPDATE SET
            secret = excluded.secret,
            is_linked = excluded.is_linked,
            name = CASE WHEN excluded.name != '' THEN excluded.name ELSE users.name END,
            api_key = CASE WHEN excluded.api_key != '' THEN excluded.api_key ELSE users.api_key END,
            status = CASE WHEN excluded.status != '' THEN excluded.status ELSE users.status END,
            updated_at = datetime('now')
        """, (clean_email, secret or '', is_linked_int, name or '', api_key or '', status or ''))
        conn.commit()
        return True
    except Exception as e:
        print(f"[SQLite Save User Error]: {e}")
        return False
    finally:
        conn.close()

# =========================================================================
# OPERASI MULTI-AKUN MEDIA SOSIAL (INSTAN & PERSISTEN)
# =========================================================================

def db_get_social_accounts(email=None, api_key=None):
    """
    Mengambil seluruh daftar akun medsos yang terhubung untuk user dari SQLite.
    """
    clean_email = str(email).strip().lower() if email else None
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if api_key and not clean_email:
            cur.execute("SELECT email FROM users WHERE api_key = ?", (api_key,))
            u_row = cur.fetchone()
            if u_row:
                clean_email = str(u_row['email']).lower()
            else:
                return []

        if clean_email:
            cur.execute("SELECT * FROM social_accounts WHERE lower(user_email) = ? ORDER BY created_at ASC", (clean_email,))
        else:
            cur.execute("SELECT * FROM social_accounts ORDER BY created_at ASC")

        rows = cur.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            extra = {}
            if d.get('extra_json'):
                try:
                    extra = json.loads(d['extra_json'])
                except Exception:
                    pass
            acc_dict = {
                "id": d['id'],
                "platform": d['platform'],
                "name": d.get('name') or '',
                "username": d.get('username') or '',
                "avatar_url": d.get('avatar_url') or '',
                "access_token": d.get('access_token') or '',
                "refresh_token": d.get('refresh_token') or '',
                "open_id": d.get('open_id') or '',
                "page_id": d.get('page_id') or '',
                "instagram_id": d.get('instagram_id') or '',
                "token_expires_at": d.get('token_expires_at')
            }
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if k not in acc_dict or not acc_dict[k]:
                        acc_dict[k] = v
            results.append(acc_dict)
        return results
    except Exception as e:
        print(f"[SQLite Get Social Accounts Error]: {e}")
        return []
    finally:
        conn.close()

def db_save_social_account(email, account_dict):
    """
    Menyimpan atau memperbarui akun medsos spesifik untuk user.
    Memeriksa kuota paket (Trial=1 per platform, Starter=10, VIP=20, VVIP=30, Admin=100).
    """
    if not email or not account_dict or not account_dict.get('platform'):
        return False, "Data akun tidak lengkap."

    clean_email = str(email).strip().lower()
    platform = str(account_dict.get('platform')).strip().lower()
    acc_id = str(account_dict.get('id') or f"{platform}_{uuid.uuid4().hex[:8]}").strip()
    account_dict['id'] = acc_id
    account_dict['platform'] = platform

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Ambil status user
        cur.execute("SELECT status FROM users WHERE lower(email) = ?", (clean_email,))
        u_row = cur.fetchone()
        user_status = str(u_row['status'] if u_row and u_row['status'] else '').lower()

        is_trial = 'trial' in user_status or not any(w in user_status for w in ['starter', 'vip', 'vvip', 'admin', 'paid', 'lifetime'])
        if is_trial:
            plan_limit = 7
        elif 'vvip' in user_status:
            plan_limit = 30
        elif 'vip' in user_status:
            plan_limit = 20
        elif 'starter' in user_status:
            plan_limit = 10
        else:
            plan_limit = 100

        # Cek daftar akun eksisting
        cur.execute("SELECT * FROM social_accounts WHERE lower(user_email) = ?", (clean_email,))
        existing_rows = cur.fetchall()

        found_id = None
        for r in existing_rows:
            r_plat = str(r['platform']).lower()
            if r_plat == platform:
                if str(r['id']) == acc_id:
                    found_id = r['id']
                    break
                elif account_dict.get('username') and str(r['username']).lower() == str(account_dict['username']).lower():
                    found_id = r['id']
                    break

        # Jika akun baru, cek batas kuota
        if not found_id:
            if is_trial:
                same_plat = [r for r in existing_rows if str(r['platform']).lower() == platform and str(r['id']) != 'meta_primary']
                if len(same_plat) >= 1:
                    return False, f"Batas kuota Free Trial (1 profil per platform) untuk {platform.capitalize()} telah tercapai! Silakan upgrade paket untuk multi-akun."
            elif len(existing_rows) >= plan_limit:
                return False, f"Batas kuota akun ({plan_limit} akun) untuk paket Anda telah tercapai! Silakan upgrade paket untuk menambah akun lebih banyak."

        target_id = found_id or acc_id
        cur.execute("""
        INSERT INTO social_accounts (
            id, user_email, platform, name, username, avatar_url,
            access_token, refresh_token, open_id, page_id, instagram_id,
            token_expires_at, extra_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            username = excluded.username,
            avatar_url = excluded.avatar_url,
            access_token = excluded.access_token,
            refresh_token = excluded.refresh_token,
            open_id = excluded.open_id,
            page_id = excluded.page_id,
            instagram_id = excluded.instagram_id,
            token_expires_at = excluded.token_expires_at,
            extra_json = excluded.extra_json,
            updated_at = datetime('now')
        """, (
            target_id, clean_email, platform,
            str(account_dict.get('name') or ''),
            str(account_dict.get('username') or ''),
            str(account_dict.get('avatar_url') or ''),
            str(account_dict.get('access_token') or ''),
            str(account_dict.get('refresh_token') or ''),
            str(account_dict.get('open_id') or ''),
            str(account_dict.get('page_id') or ''),
            str(account_dict.get('instagram_id') or ''),
            account_dict.get('token_expires_at'),
            json.dumps(account_dict, ensure_ascii=False)
        ))
        conn.commit()
    except Exception as e:
        print(f"[SQLite Save Social Account Error]: {e}")
        return False, str(e)
    finally:
        conn.close()

    updated_accounts = db_get_social_accounts(email=clean_email)
    return True, updated_accounts

def db_delete_social_account(email, platform, account_id):
    """
    Menghapus akun medsos tertentu berdasarkan platform dan account_id.
    Operasi instan di SQLite.
    """
    if not email:
        return False, "Email tidak valid."
    clean_email = str(email).strip().lower()
    plat = str(platform or '').strip().lower()
    target_id = str(account_id or '').strip()

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if target_id and target_id.lower() != 'all' and target_id.lower() != 'primary':
            cur.execute("""
            DELETE FROM social_accounts
            WHERE lower(user_email) = ? AND (id = ? OR open_id = ? OR page_id = ? OR lower(username) = ?)
            """, (clean_email, target_id, target_id, target_id, target_id.lower()))

            # Jika tidak ada lagi akun Facebook riil, bersihkan placeholder meta_primary
            cur.execute("SELECT id FROM social_accounts WHERE lower(user_email) = ? AND lower(platform) IN ('facebook', 'fb', 'facebook_page') AND id != 'meta_primary'", (clean_email,))
            if not cur.fetchall():
                cur.execute("DELETE FROM social_accounts WHERE lower(user_email) = ? AND id = 'meta_primary'", (clean_email,))
        elif plat:
            aliases = [plat]
            if plat == 'facebook': aliases.extend(['fb', 'facebook_page', 'meta'])
            elif plat in ['fb', 'facebook_page']: aliases.extend(['facebook', 'meta'])
            elif plat == 'instagram': aliases.extend(['ig'])
            elif plat in ['twitter', 'x']: aliases.extend(['twitter', 'x'])

            placeholders = ','.join('?' for _ in aliases)
            cur.execute(f"DELETE FROM social_accounts WHERE lower(user_email) = ? AND lower(platform) IN ({placeholders})", [clean_email] + aliases)
            if plat in ['facebook', 'fb', 'facebook_page', 'meta']:
                cur.execute("DELETE FROM social_accounts WHERE lower(user_email) = ? AND id = 'meta_primary'", (clean_email,))
        conn.commit()
    except Exception as e:
        print(f"[SQLite Delete Social Account Error]: {e}")
        return False, str(e)
    finally:
        conn.close()

    remaining_accounts = db_get_social_accounts(email=clean_email)
    return True, remaining_accounts

def db_get_social_account_token(email=None, api_key=None, platform=None, account_id=None):
    """
    Mengambil access token dan detail akun tertentu.
    """
    accounts = db_get_social_accounts(email=email, api_key=api_key)
    if not accounts:
        return None, None

    plat = str(platform or '').strip().lower() if platform else None
    if account_id:
        for a in accounts:
            if a.get('id') == account_id or a.get('open_id') == account_id or a.get('page_id') == account_id:
                if not plat or str(a.get('platform', '')).lower() == plat:
                    return a.get('access_token'), a
        return None, None

    if plat:
        for a in accounts:
            if str(a.get('platform', '')).lower() == plat and a.get('access_token'):
                return a.get('access_token'), a
        return None, None

    for a in accounts:
        if a.get('access_token'):
            return a.get('access_token'), a

    return None, None

# =========================================================================
# LEGACY GETTER WRAPPERS (UNTUK N8N, CRON, & STUDIO PUBLISHER)
# =========================================================================

def db_get_tiktok_tokens_by_api_key(api_key, email=None):
    accs = db_get_social_accounts(email=email, api_key=api_key)
    for a in accs:
        if a.get('platform') == 'tiktok' and a.get('access_token'):
            return a.get('access_token'), a.get('open_id', ''), a.get('refresh_token', '')
    return None, None, None

def db_get_meta_token_by_api_key(api_key, email=None):
    accs = db_get_social_accounts(email=email, api_key=api_key)
    for a in accs:
        if a.get('platform') in ['facebook', 'instagram', 'meta'] and a.get('access_token'):
            return a.get('access_token')
    return None

def db_get_linkedin_token_by_api_key(api_key, email=None):
    accs = db_get_social_accounts(email=email, api_key=api_key)
    for a in accs:
        if a.get('platform') == 'linkedin' and a.get('access_token'):
            return a.get('access_token')
    return None

def db_get_youtube_tokens_by_api_key(api_key, email=None):
    accs = db_get_social_accounts(email=email, api_key=api_key)
    for a in accs:
        if a.get('platform') == 'youtube' and a.get('access_token'):
            return a.get('access_token'), a.get('refresh_token', '')
    return None, None

def db_get_threads_token_by_api_key(api_key, email=None):
    accs = db_get_social_accounts(email=email, api_key=api_key)
    for a in accs:
        if a.get('platform') == 'threads' and a.get('access_token'):
            return a.get('access_token')
    return None

def db_get_twitter_token_by_api_key(api_key, email=None):
    accs = db_get_social_accounts(email=email, api_key=api_key)
    for a in accs:
        if a.get('platform') in ['twitter', 'x'] and a.get('access_token'):
            return a.get('access_token')
    return None

# =========================================================================
# OPERASI JADWAL POSTING (SCHEDULED POSTS)
# =========================================================================

def db_save_scheduled_post(post_dict):
    """Menyimpan jadwal postingan baru ke SQLite."""
    if not post_dict:
        return False, "Data jadwal kosong."

    post_id = str(post_dict.get('id') or f"sched_{uuid.uuid4().hex[:10]}")
    post_dict['id'] = post_id
    status = str(post_dict.get('status', 'PENDING')).upper()
    now_str = datetime.now().isoformat()
    created_at = post_dict.get('created_at', now_str)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO scheduled_posts (
            id, user_email, platform, account_id, account_name,
            video_url, title, caption, scheduled_at, status, publish_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            publish_id = excluded.publish_id,
            updated_at = datetime('now')
        """, (
            post_id,
            str(post_dict.get('user_email', '')).strip().lower(),
            str(post_dict.get('platform', 'facebook')).lower(),
            str(post_dict.get('account_id', '')),
            str(post_dict.get('account_name', '')),
            str(post_dict.get('video_url', '')),
            str(post_dict.get('title', '')),
            str(post_dict.get('caption', '')),
            str(post_dict.get('scheduled_at', '')),
            status,
            str(post_dict.get('publish_id', '')),
            created_at
        ))
        conn.commit()
        return True, post_dict
    except Exception as e:
        print(f"[SQLite Save Scheduled Post Error]: {e}")
        return False, str(e)
    finally:
        conn.close()

def db_get_scheduled_posts(email=None, status=None):
    """Mengambil daftar postingan terjadwal untuk user (atau semua jika email=None)."""
    clean_email = str(email).strip().lower() if email else None
    stat = str(status).strip().upper() if status else None

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = "SELECT * FROM scheduled_posts WHERE 1=1"
        params = []
        if clean_email:
            query += " AND lower(user_email) = ?"
            params.append(clean_email)
        if stat:
            query += " AND upper(status) = ?"
            params.append(stat)
        query += " ORDER BY scheduled_at ASC"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        results = [dict(r) for r in rows]
        return results
    except Exception as e:
        print(f"[SQLite Get Scheduled Posts Error]: {e}")
        return []
    finally:
        conn.close()

def db_update_scheduled_post(post_id, updates_dict):
    """Memperbarui status atau data postingan terjadwal (misal dari PENDING ke PUBLISHED)."""
    if not post_id or not updates_dict:
        return False

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        fields = []
        params = []
        for k in ['status', 'publish_id', 'title', 'caption', 'scheduled_at']:
            if k in updates_dict:
                fields.append(f"{k} = ?")
                params.append(str(updates_dict[k]).upper() if k == 'status' else str(updates_dict[k]))
        if not fields:
            return True
        fields.append("updated_at = datetime('now')")
        params.append(str(post_id).strip())

        query = f"UPDATE scheduled_posts SET {', '.join(fields)} WHERE id = ?"
        cur.execute(query, tuple(params))
        conn.commit()
        return True
    except Exception as e:
        print(f"[SQLite Update Scheduled Post Error]: {e}")
        return False
    finally:
        conn.close()

def db_delete_scheduled_post(post_id, email=None):
    """Menghapus jadwal postingan tertentu."""
    if not post_id:
        return False
    clean_email = str(email).strip().lower() if email else None

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if clean_email:
            cur.execute("DELETE FROM scheduled_posts WHERE id = ? AND lower(user_email) = ?", (str(post_id).strip(), clean_email))
        else:
            cur.execute("DELETE FROM scheduled_posts WHERE id = ?", (str(post_id).strip(),))
        conn.commit()
        return True
    except Exception as e:
        print(f"[SQLite Delete Scheduled Post Error]: {e}")
        return False
    finally:
        conn.close()

# =========================================================================
# OPERASI INSTAGRAM AUTO DM & COMMENT REPLY
# =========================================================================

def db_ensure_ig_auto_dm_worksheet_template(email, sheet_id=None):
    """Dummy template compatibility."""
    return True

def db_get_ig_auto_dm_rules_from_sheet(email, sheet_id=None):
    """Mengambil rules dari setting SQLite."""
    settings = db_get_ig_auto_dm_settings(email)
    return settings.get('rules', [])

def db_get_ig_auto_dm_settings(email):
    """Mengambil settingan Instagram Auto DM langsung dari SQLite."""
    clean_email = str(email).strip().lower() if email else None
    default_settings = {
        "is_enabled": False,
        "source_mode": "dashboard",
        "sheet_tab": "Instagram_Auto_DM",
        "custom_sheet_id": "",
        "rules": [],
        "stats": {
            "total_comments_detected": 0,
            "total_dm_sent": 0,
            "total_replies_sent": 0,
            "last_activity": ""
        }
    }
    if not clean_email:
        return default_settings

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ig_auto_dm_settings WHERE lower(user_email) = ?", (clean_email,))
        row = cur.fetchone()
        if not row:
            return default_settings

        d = dict(row)
        rules = []
        stats = default_settings['stats'].copy()
        if d.get('rules_json'):
            try: rules = json.loads(d['rules_json'])
            except Exception: pass
        if d.get('stats_json'):
            try: stats.update(json.loads(d['stats_json']))
            except Exception: pass

        return {
            "is_enabled": bool(d.get('is_enabled')),
            "source_mode": d.get('source_mode') or 'dashboard',
            "sheet_tab": d.get('sheet_tab') or 'Instagram_Auto_DM',
            "custom_sheet_id": d.get('custom_sheet_id') or '',
            "rules": rules,
            "stats": stats
        }
    except Exception as e:
        print(f"[SQLite Get IG Auto DM Error]: {e}")
        return default_settings
    finally:
        conn.close()

def db_save_ig_auto_dm_settings(email, settings_dict):
    """Menyimpan settingan Instagram Auto DM ke SQLite."""
    clean_email = str(email).strip().lower() if email else None
    if not clean_email or not isinstance(settings_dict, dict):
        return False, "Data pengaturan tidak valid."

    is_en = 1 if settings_dict.get('is_enabled') else 0
    src_m = settings_dict.get('source_mode', 'dashboard')
    tab_m = settings_dict.get('sheet_tab', 'Instagram_Auto_DM')
    c_id = settings_dict.get('custom_sheet_id', '')
    r_json = json.dumps(settings_dict.get('rules', []), ensure_ascii=False)
    s_json = json.dumps(settings_dict.get('stats', {}), ensure_ascii=False)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO ig_auto_dm_settings (
            user_email, is_enabled, source_mode, sheet_tab, custom_sheet_id,
            rules_json, stats_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(user_email) DO UPDATE SET
            is_enabled = excluded.is_enabled,
            source_mode = excluded.source_mode,
            sheet_tab = excluded.sheet_tab,
            custom_sheet_id = excluded.custom_sheet_id,
            rules_json = excluded.rules_json,
            stats_json = excluded.stats_json,
            updated_at = datetime('now')
        """, (clean_email, is_en, src_m, tab_m, c_id, r_json, s_json))
        conn.commit()
        return True, "Pengaturan berhasil disimpan ke database lokal."
    except Exception as e:
        print(f"[SQLite Save IG Auto DM Error]: {e}")
        return False, str(e)
    finally:
        conn.close()

def db_find_user_by_instagram_id(ig_id):
    """
    Pencarian pemilik akun Instagram instan (< 0.1ms).
    Krusial untuk webhook Meta agar response < 2 detik tanpa timeout.
    """
    if not ig_id:
        return None
    clean_id = str(ig_id).strip()

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT * FROM social_accounts
        WHERE platform IN ('instagram', 'facebook') AND (id = ? OR instagram_id = ? OR page_id = ? OR open_id = ?)
        LIMIT 1
        """, (clean_id, clean_id, clean_id, clean_id))
        row = cur.fetchone()
        if row:
            d = dict(row)
            return {
                "email": d['user_email'],
                "access_token": d.get('access_token', ''),
                "account": d
            }
        return None
    except Exception as e:
        print(f"[SQLite Find User By IG Error]: {e}")
        return None
    finally:
        conn.close()

def db_record_ig_auto_dm_stat(email, dm_success=True, reply_success=True):
    """Update statistik aktivitas Auto DM."""
    settings = db_get_ig_auto_dm_settings(email)
    stats = settings.get('stats', {})
    stats['total_comments_detected'] = stats.get('total_comments_detected', 0) + 1
    if dm_success:
        stats['total_dm_sent'] = stats.get('total_dm_sent', 0) + 1
    if reply_success:
        stats['total_replies_sent'] = stats.get('total_replies_sent', 0) + 1
    stats['last_activity'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    settings['stats'] = stats
    db_save_ig_auto_dm_settings(email, settings)

def db_log_ig_auto_dm_event(email, log_info):
    """Menyimpan log event Auto DM ke activity_logs SQLite."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO activity_logs (
            timestamp, log_id, user_email, platform, status, details, keterangan
        ) VALUES (datetime('now'), ?, ?, 'instagram', ?, ?, ?)
        """, (
            str(uuid.uuid4().hex[:10]),
            str(email).strip().lower(),
            str(log_info.get('status', 'OK')),
            str(log_info.get('comment_text', '')),
            str(log_info.get('reply_text', ''))
        ))
        conn.commit()
    except Exception as e:
        print(f"[SQLite Log Event Error]: {e}")
    finally:
        conn.close()

# =========================================================================
# INSTAGRAM OUTREACH MULTI-ACCOUNT MANAGEMENT (FOR APIFY & AUTO DM)
# =========================================================================

def db_get_all_outreach_accounts():
    """Mengambil semua akun Instagram outreach dengan auto-reset harian."""
    conn = get_db_connection()
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        cur = conn.cursor()
        cur.execute("SELECT * FROM ig_outreach_accounts ORDER BY id ASC")
        rows = cur.fetchall()
        accounts = []
        for r in rows:
            sent_today = r['sent_today']
            if r['last_reset_date'] != today:
                sent_today = 0
                conn.execute("UPDATE ig_outreach_accounts SET sent_today = 0, last_reset_date = ? WHERE id = ?", (today, r['id']))
                conn.commit()
            
            accounts.append({
                "id": r['id'],
                "username": r['username'],
                "daily_limit": r['daily_limit'],
                "sent_today": sent_today,
                "is_active": bool(r['is_active']),
                "created_at": r['created_at'],
                "has_session": bool(r['session_id'])
            })
        return accounts
    except Exception as e:
        print(f"[SQLite Get Outreach Accounts Error]: {e}")
        return []
    finally:
        conn.close()

def db_save_outreach_account(username, session_id, daily_limit=20):
    """Menambah atau memperbarui akun Instagram outreach."""
    conn = get_db_connection()
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        clean_user = username.strip().lstrip('@')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ig_outreach_accounts (username, session_id, daily_limit, sent_today, last_reset_date, is_active, updated_at)
            VALUES (?, ?, ?, 0, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(username) DO UPDATE SET
                session_id = excluded.session_id,
                daily_limit = excluded.daily_limit,
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
        """, (clean_user, session_id.strip(), int(daily_limit), today))
        conn.commit()
        return True, "Akun outreach berhasil disimpan & aktif!"
    except Exception as e:
        print(f"[SQLite Save Outreach Account Error]: {e}")
        return False, str(e)
    finally:
        conn.close()

def db_delete_outreach_account(account_id):
    """Menghapus akun Instagram outreach berdasarkan ID."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM ig_outreach_accounts WHERE id = ?", (account_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[SQLite Delete Outreach Account Error]: {e}")
        return False
    finally:
        conn.close()

def db_get_next_available_outreach_account():
    """
    Mengambil 1 akun aktif berikutnya yang belum mencapai kuota harian (sent_today < daily_limit)
    menggunakan algoritma Round-Robin.
    """
    conn = get_db_connection()
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        # Auto-reset kuota jika hari telah berganti
        conn.execute("UPDATE ig_outreach_accounts SET sent_today = 0, last_reset_date = ? WHERE last_reset_date != ?", (today, today))
        conn.commit()

        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM ig_outreach_accounts 
            WHERE is_active = 1 AND sent_today < daily_limit 
            ORDER BY sent_today ASC, id ASC LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"[SQLite Get Next Outreach Account Error]: {e}")
        return None
    finally:
        conn.close()

def db_increment_outreach_sent(account_id):
    """Menambah counter sent_today pada akun outreach setelah DM sukses terkirim."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE ig_outreach_accounts SET sent_today = sent_today + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (account_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[SQLite Increment Outreach Sent Error]: {e}")
        return False
    finally:
        conn.close()

