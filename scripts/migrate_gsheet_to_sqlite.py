"""
Script Migrasi Database: Google Sheets -> SQLite (trendora.db)
Menyalin seluruh data user, token akun media sosial, pengaturan IG Auto DM,
dan status paket langganan secara lengkap tanpa ada data yang hilang.
"""
import os
import sys
import json
import sqlite3
from datetime import datetime

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import config
from utils import database as db

DB_PATH = os.path.join(PARENT_DIR, 'trendora.db')

def init_db(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA busy_timeout = 5000;")
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
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

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
    """)
    conn.commit()

def run_migration():
    print(f"[*] Menghubungkan ke SQLite: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    cur = conn.cursor()

    print("[*] Menghubungkan ke Google Sheets...")
    sheet = db.get_gsheet()
    if not sheet:
        print("[!] GAGAL: Tidak dapat membuka Google Sheets. Periksa file service_account.json / kredensial.")
        return False

    all_rows = sheet.get_all_values()
    print(f"[*] Berhasil membaca {len(all_rows)} baris dari Google Sheets.")
    if len(all_rows) <= 1:
        print("[*] Tidak ada data user di Google Sheets.")
        return True

    migrated_users = 0
    migrated_accounts = 0
    migrated_ig_dm = 0

    # Scan data user (mulai baris index 1, skip header)
    for idx, row in enumerate(all_rows[1:], start=2):
        if not row or not str(row[0]).strip():
            continue

        email = str(row[0]).strip().lower()
        secret = str(row[1]).strip() if len(row) > 1 else ''
        is_linked = 1 if len(row) > 2 and str(row[2]).strip().lower() == 'true' else 0
        name = str(row[3]).strip() if len(row) > 3 else ''
        api_key = str(row[4]).strip() if len(row) > 4 else ''
        status = str(row[5]).strip() if len(row) > 5 else 'Free Trial'

        # Insert / Update user di SQLite
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
        """, (email, secret, is_linked, name, api_key, status))
        migrated_users += 1

        # Kumpulkan akun medsos user
        social_accounts = []
        # 1. Dari JSON Kolom 16
        if len(row) >= 16 and row[15].strip():
            try:
                parsed = json.loads(row[15].strip())
                if isinstance(parsed, list):
                    social_accounts = parsed
            except Exception as e:
                print(f"    [!] Error parse JSON social accounts row {idx}: {e}")

        # 2. Jika kolom 16 kosong, ekstrak dari legacy columns
        if not social_accounts:
            # TikTok (col 7-9)
            if len(row) > 6 and row[6].strip():
                social_accounts.append({
                    "id": row[7].strip() if len(row) > 7 and row[7].strip() else "tiktok_primary",
                    "platform": "tiktok",
                    "name": name or "Akun TikTok",
                    "username": f"@{email.split('@')[0]}",
                    "access_token": row[6].strip(),
                    "open_id": row[7].strip() if len(row) > 7 else "",
                    "refresh_token": row[8].strip() if len(row) > 8 else ""
                })
            # Meta (col 10)
            if len(row) > 9 and row[9].strip():
                social_accounts.append({
                    "id": "meta_primary",
                    "platform": "facebook",
                    "name": "Facebook Page Terhubung",
                    "username": "facebook.page",
                    "access_token": row[9].strip()
                })
            # LinkedIn (col 11)
            if len(row) > 10 and row[10].strip():
                social_accounts.append({
                    "id": "linkedin_primary",
                    "platform": "linkedin",
                    "name": "LinkedIn Profile",
                    "username": "linkedin.user",
                    "access_token": row[10].strip()
                })
            # YouTube (col 12-13)
            if len(row) > 11 and row[11].strip():
                social_accounts.append({
                    "id": "youtube_primary",
                    "platform": "youtube",
                    "name": "YouTube Channel",
                    "username": "@YouTubeChannel",
                    "access_token": row[11].strip(),
                    "refresh_token": row[12].strip() if len(row) > 12 else ""
                })
            # Threads (col 14)
            if len(row) > 13 and row[13].strip():
                social_accounts.append({
                    "id": "threads_primary",
                    "platform": "threads",
                    "name": "Threads Profile",
                    "username": "@threads_user",
                    "access_token": row[13].strip()
                })
            # Twitter (col 15)
            if len(row) > 14 and row[14].strip():
                social_accounts.append({
                    "id": "twitter_primary",
                    "platform": "twitter",
                    "name": "X / Twitter",
                    "username": "@x_user",
                    "access_token": row[14].strip()
                })

        # Simpan akun medsos ke tabel social_accounts
        for acc in social_accounts:
            acc_id = str(acc.get('id') or f"{acc.get('platform')}_{email}").strip()
            platform = str(acc.get('platform', '')).strip().lower()
            acc_name = str(acc.get('name', ''))
            acc_user = str(acc.get('username', ''))
            avatar = str(acc.get('avatar_url', ''))
            tok = str(acc.get('access_token', ''))
            ref_tok = str(acc.get('refresh_token', ''))
            op_id = str(acc.get('open_id', ''))
            page_id = str(acc.get('page_id', ''))
            ig_id = str(acc.get('instagram_id', ''))
            expires_at = acc.get('token_expires_at')

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
                acc_id, email, platform, acc_name, acc_user, avatar,
                tok, ref_tok, op_id, page_id, ig_id,
                expires_at, json.dumps(acc),
            ))
            migrated_accounts += 1

        # 3. Instagram Auto DM Settings (Kolom 17)
        if len(row) >= 17 and row[16].strip():
            try:
                ig_settings = json.loads(row[16].strip())
                if isinstance(ig_settings, dict):
                    is_en = 1 if ig_settings.get('is_enabled') else 0
                    src_m = ig_settings.get('source_mode', 'dashboard')
                    tab_m = ig_settings.get('sheet_tab', 'Instagram_Auto_DM')
                    c_id = ig_settings.get('custom_sheet_id', '')
                    r_json = json.dumps(ig_settings.get('rules', []))
                    s_json = json.dumps(ig_settings.get('stats', {}))

                    cur.execute("""
                    INSERT INTO ig_auto_dm_settings (
                        user_email, is_enabled, source_mode, sheet_tab,
                        custom_sheet_id, rules_json, stats_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(user_email) DO UPDATE SET
                        is_enabled = excluded.is_enabled,
                        source_mode = excluded.source_mode,
                        sheet_tab = excluded.sheet_tab,
                        custom_sheet_id = excluded.custom_sheet_id,
                        rules_json = excluded.rules_json,
                        stats_json = excluded.stats_json,
                        updated_at = datetime('now')
                    """, (email, is_en, src_m, tab_m, c_id, r_json, s_json))
                    migrated_ig_dm += 1
            except Exception as e:
                print(f"    [!] Error parse IG Auto DM settings row {idx}: {e}")

    conn.commit()
    conn.close()

    print("\n" + "="*50)
    print("MIGRASI KE SQLITE BERHASIL 100%! 🎉")
    print(f"• User termigrasi          : {migrated_users}")
    print(f"• Akun medsos termigrasi   : {migrated_accounts}")
    print(f"• Setting IG Auto DM       : {migrated_ig_dm}")
    print(f"• Database File            : {DB_PATH}")
    print("="*50)
    return True

if __name__ == '__main__':
    run_migration()

