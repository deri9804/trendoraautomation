import os
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from flask import Blueprint, request, jsonify, session

import config
from utils import database as db

ig_auto_dm_bp = Blueprint('instagram_auto_dm', __name__)

# Cache sederhana untuk deduplikasi comment_id (mencegah double reply jika Meta mengirim webhook berulang)
_PROCESSED_COMMENTS = {}

def is_comment_processed(comment_id):
    now = time.time()
    # Bersihkan cache lama (> 1 jam)
    expired_keys = [k for k, t in _PROCESSED_COMMENTS.items() if now - t > 3600]
    for k in expired_keys:
        _PROCESSED_COMMENTS.pop(k, None)
    return str(comment_id) in _PROCESSED_COMMENTS

def mark_comment_processed(comment_id):
    _PROCESSED_COMMENTS[str(comment_id)] = time.time()

# =========================================================================
# META GRAPH API HELPERS (PRIVATE REPLIES & PUBLIC REPLIES)
# =========================================================================

def send_instagram_private_reply(ig_user_id, comment_id, text, access_token):
    """
    Mengirim pesan langsung (Private Reply) ke pengguna yang berkomentar via Meta Graph API v21.0.
    Meta mewajibkan recipient berupa object {'comment_id': '<COMMENT_ID>'}.
    """
    if not comment_id or not text or not access_token:
        return False, "Parameter tidak lengkap."

    payload = {
        "recipient": {
            "comment_id": str(comment_id)
        },
        "message": {
            "text": str(text)
        }
    }
    data_bytes = json.dumps(payload).encode('utf-8')
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Coba endpoint spesifik akun Instagram terlebih dahulu
    endpoints_to_try = [
        f"https://graph.facebook.com/v21.0/{ig_user_id}/messages" if ig_user_id else None,
        "https://graph.facebook.com/v21.0/me/messages"
    ]
    last_err = ""

    for url in endpoints_to_try:
        if not url:
            continue
        try:
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                return True, res
        except urllib.error.HTTPError as he:
            err_body = he.read().decode('utf-8')
            last_err = f"HTTP {he.code}: {err_body}"
            print(f"[IG Private Reply HTTP Error on {url}]: {last_err}")
        except Exception as e:
            last_err = str(e)
            print(f"[IG Private Reply Exception on {url}]: {last_err}")

    return False, last_err

def send_instagram_public_reply(comment_id, text, access_token):
    """
    Membalas komentar secara publik di postingan/Reels via Meta Graph API v21.0.
    """
    if not comment_id or not text or not access_token:
        return False, "Parameter tidak lengkap."

    url = f"https://graph.facebook.com/v21.0/{comment_id}/replies"
    payload = {
        "message": str(text)
    }
    data_bytes = json.dumps(payload).encode('utf-8')
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            return True, res
    except urllib.error.HTTPError as he:
        err_body = he.read().decode('utf-8')
        print(f"[IG Public Reply HTTP Error]: {he.code} - {err_body}")
        return False, err_body
    except Exception as e:
        print(f"[IG Public Reply Exception]: {e}")
        return False, str(e)

# =========================================================================
# WEBHOOK ENDPOINT FOR META INSTAGRAM EVENTS
# =========================================================================

@ig_auto_dm_bp.route('/api/webhook/instagram', methods=['GET', 'POST'])
def instagram_webhook():
    """
    Webhook resmi Meta untuk Instagram.
    - GET: Verifikasi langganan webhook (hub.mode, hub.verify_token, hub.challenge)
    - POST: Menangkap event komentar baru secara real-time dan mengeksekusi Auto Comment + Auto DM.
    """
    # 1. VERIFIKASI WEBHOOK DARI META DASHBOARD (GET)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        expected_token = getattr(config, 'META_WEBHOOK_VERIFY_TOKEN', 'trendora_meta_secret_123')
        if mode == 'subscribe' and token == expected_token:
            print(f"[Meta IG Webhook]: Handshake Verifikasi Sukses! Challenge={challenge}")
            return challenge, 200, {'Content-Type': 'text/plain'}
        else:
            print(f"[Meta IG Webhook]: Verifikasi Gagal! mode={mode}, token={token}")
            return "Forbidden", 403

    # 2. EVENT LISTENER KOMENTAR MASUK (POST)
    try:
        raw_data = request.get_json(force=True, silent=True) or {}
        print(f"[Meta IG Webhook Event Received]: {json.dumps(raw_data)[:300]}")

        # Meta mengirim object == 'instagram'
        if raw_data.get('object') == 'instagram':
            for entry in raw_data.get('entry', []):
                ig_user_id = str(entry.get('id', '')).strip()
                for change in entry.get('changes', []):
                    if change.get('field') == 'comments':
                        val = change.get('value', {})
                        comment_id = str(val.get('id', '')).strip()
                        comment_text = (val.get('text') or '').strip()
                        from_user = val.get('from', {})
                        commenter_id = str(from_user.get('id', '')).strip()
                        commenter_username = (from_user.get('username') or '').strip()

                        if not comment_id or not comment_text:
                            continue

                        # Jangan balas komentar dari akun bot sendiri
                        if commenter_id and commenter_id == ig_user_id:
                            continue

                        # Cegah double execution
                        if is_comment_processed(comment_id):
                            continue
                        mark_comment_processed(comment_id)

                        # Cari pemilik akun Instagram di database Trendora
                        user_info = db.db_find_user_by_instagram_id(ig_user_id)
                        if not user_info:
                            print(f"[IG Auto DM Warning]: Akun Instagram ID {ig_user_id} belum terdaftar di Trendora.")
                            continue

                        email = user_info.get('email')
                        access_token = user_info.get('access_token')

                        # Ambil konfigurasi Auto DM user
                        settings = db.db_get_ig_auto_dm_settings(email)
                        if not settings.get('is_enabled', False):
                            print(f"[IG Auto DM]: Bot non-aktif untuk user {email}")
                            continue

                        # Ambil aturan (rules) berdasarkan pilihan user: 'dashboard' atau 'spreadsheet'
                        source_mode = settings.get('source_mode', 'dashboard')
                        if source_mode == 'spreadsheet':
                            rules = db.db_get_ig_auto_dm_rules_from_sheet(email, sheet_id=settings.get('custom_sheet_id'))
                        else:
                            rules = settings.get('rules', [])

                        if not rules:
                            print(f"[IG Auto DM]: Tidak ada aturan aktif untuk mode {source_mode} ({email})")
                            continue

                        # Evaluasi kata kunci yang cocok
                        matched_rule = None
                        clean_text = comment_text.lower()
                        for r in rules:
                            if not r.get('is_active', True):
                                continue
                            kw = str(r.get('keyword', '')).strip().lower()
                            if not kw:
                                continue
                            m_type = str(r.get('match_type', 'contains')).lower()

                            if kw in ['*', 'all', 'semua']:
                                matched_rule = r
                                break
                            elif m_type == 'exact':
                                if clean_text == kw:
                                    matched_rule = r
                                    break
                            else: # contains
                                if kw in clean_text:
                                    matched_rule = r
                                    break

                        if not matched_rule:
                            print(f"[IG Auto DM]: Tidak ada kata kunci yang cocok dengan komentar '{comment_text}'")
                            continue

                        # Siapkan teks balasan dan personalisasi variabel {username}
                        dm_template = matched_rule.get('dm_reply', '').strip()
                        comment_template = matched_rule.get('comment_reply', '').strip()

                        if commenter_username:
                            dm_template = dm_template.replace('{username}', f"@{commenter_username}")
                            comment_template = comment_template.replace('{username}', f"@{commenter_username}")

                        dm_ok = False
                        comment_ok = False

                        # 1. Kirim Private Reply (Auto DM)
                        if dm_template:
                            dm_ok, dm_res = send_instagram_private_reply(ig_user_id, comment_id, dm_template, access_token)
                            print(f"[IG Auto DM Result]: DM Sent={dm_ok} to @{commenter_username}")

                        # 2. Balas Komentar Publik
                        if comment_template:
                            comment_ok, comm_res = send_instagram_public_reply(comment_id, comment_template, access_token)
                            print(f"[IG Auto Comment Reply Result]: Comment Reply={comment_ok} on {comment_id}")

                        # 3. Update Statistik & Log Aktivitas
                        db.db_record_ig_auto_dm_stat(email, dm_success=dm_ok, reply_success=comment_ok)
                        log_entry = {
                            "comment_id": comment_id,
                            "commenter_username": commenter_username,
                            "comment_text": comment_text,
                            "keyword_matched": matched_rule.get('keyword'),
                            "source_mode": source_mode,
                            "dm_success": dm_ok,
                            "reply_success": comment_ok,
                            "timestamp": datetime.now().isoformat()
                        }
                        db.db_log_ig_auto_dm_event(email, log_entry)

        return jsonify({"status": "SUCCESS", "message": "Event processed"}), 200
    except Exception as e:
        print(f"[IG Webhook Execution Error]: {e}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500


# =========================================================================
# DASHBOARD CONFIGURATION APIS
# =========================================================================

@ig_auto_dm_bp.route('/api/instagram-auto-dm/settings', methods=['GET'])
def get_ig_auto_dm_settings_api():
    """
    Mengambil data pengaturan Auto DM, statistik, daftar akun IG terhubung,
    serta aturan aktif (baik dari Dashboard maupun Spreadsheet).
    """
    session_email = session.get('user_email', '').strip().lower()
    api_key = (request.headers.get('X-API-Key') or request.args.get('api_key') or '').strip()

    email = session_email
    if not email and api_key:
        sheet_u = db.get_gsheet()
        if sheet_u:
            try:
                for r in sheet_u.get_all_values()[1:]:
                    if len(r) >= 5 and str(r[4]).strip() == api_key:
                        email = str(r[0]).strip().lower()
                        break
            except Exception:
                pass

    if not email:
        email = "deripernandi99@gmail.com"

    settings = db.db_get_ig_auto_dm_settings(email)
    source_mode = settings.get('source_mode', 'dashboard')

    # Ambil daftar akun Instagram yang terhubung
    all_social = db.db_get_social_accounts(email=email)
    ig_accounts = [a for a in all_social if str(a.get('platform', '')).lower() in ['instagram', 'ig']]
    if not ig_accounts:
        try:
            from routes.oauth_social import db_sync_instagram_from_connected_facebook_pages
            added = db_sync_instagram_from_connected_facebook_pages(email)
            if added:
                all_social = db.db_get_social_accounts(email=email)
                ig_accounts = [a for a in all_social if str(a.get('platform', '')).lower() in ['instagram', 'ig']]
        except Exception as e_heal:
            print(f"[Instagram Auto DM Heal Error]: {e_heal}")

    custom_sheet_id = settings.get('custom_sheet_id', '').strip()
    user_sheet_url = f"https://docs.google.com/spreadsheets/d/{custom_sheet_id}/edit" if custom_sheet_id else ""
    service_account_email = "trendoraautomation@websitetrendora.iam.gserviceaccount.com"

    sheet_rules = []
    sheet_status_msg = ""
    if custom_sheet_id:
        try:
            sheet_rules = db.db_get_ig_auto_dm_rules_from_sheet(email, sheet_id=custom_sheet_id)
            if sheet_rules:
                sheet_status_msg = f"{len(sheet_rules)} aturan aktif terhubung dari Google Spreadsheet Anda."
            else:
                sheet_status_msg = "Google Spreadsheet terhubung, tab Instagram_Auto_DM siap digunakan."
        except Exception as e_sheet:
            sheet_status_msg = f"Kendala membaca spreadsheet: {e_sheet}"
    else:
        sheet_status_msg = "Belum ada Google Spreadsheet yang ditautkan. Silakan tempelkan link spreadsheet Anda."

    return jsonify({
        "success": True,
        "email": email,
        "is_enabled": settings.get('is_enabled', False),
        "source_mode": source_mode,
        "sheet_tab": settings.get('sheet_tab', 'Instagram_Auto_DM'),
        "custom_sheet_id": custom_sheet_id,
        "user_sheet_url": user_sheet_url,
        "service_account_email": service_account_email,
        "dashboard_rules": settings.get('rules', []),
        "spreadsheet_rules": sheet_rules,
        "sheet_status_message": sheet_status_msg,
        "stats": settings.get('stats', {
            "total_comments_detected": 0,
            "total_dm_sent": 0,
            "total_replies_sent": 0,
            "last_activity": ""
        }),
        "connected_instagram_accounts": ig_accounts,
        "webhook_url": "https://trendoraautomation.my.id/api/webhook/instagram",
        "webhook_verify_token": getattr(config, 'META_WEBHOOK_VERIFY_TOKEN', 'trendora_meta_secret_123')
    })

@ig_auto_dm_bp.route('/api/instagram-auto-dm/settings', methods=['POST'])
def save_ig_auto_dm_settings_api():
    """
    Menyimpan perubahan pengaturan Auto DM (Saklar On/Off, Mode Dashboard/Spreadsheet, Aturan).
    """
    session_email = session.get('user_email', '').strip().lower()
    data = request.json or {}
    email = session_email or data.get('email', '').strip().lower()

    if not email:
        email = "deripernandi99@gmail.com"

    current = db.db_get_ig_auto_dm_settings(email)
    
    if 'is_enabled' in data:
        current['is_enabled'] = bool(data['is_enabled'])
    if 'source_mode' in data:
        current['source_mode'] = str(data['source_mode']).strip().lower()
    if 'sheet_tab' in data:
        current['sheet_tab'] = str(data['sheet_tab']).strip()
    if 'custom_sheet_id' in data:
        raw_sheet = str(data['custom_sheet_id']).strip()
        if '/d/' in raw_sheet:
            raw_sheet = raw_sheet.split('/d/')[1].split('/')[0].split('?')[0].strip()
        current['custom_sheet_id'] = raw_sheet
    if 'rules' in data and isinstance(data['rules'], list):
        current['rules'] = data['rules']

    ok, msg = db.db_save_ig_auto_dm_settings(email, current)
    return jsonify({
        "success": ok,
        "message": msg if ok else f"Gagal menyimpan: {msg}",
        "settings": current
    })

@ig_auto_dm_bp.route('/api/instagram-auto-dm/create-sheet-template', methods=['POST'])
def create_ig_auto_dm_sheet_template():
    """
    Membuat tab 'Instagram_Auto_DM' secara otomatis di Google Spreadsheet pribadi milik user.
    """
    session_email = session.get('user_email', '').strip().lower()
    data = request.json or {}
    email = session_email or data.get('email', '').strip().lower() or "deripernandi99@gmail.com"

    settings = db.db_get_ig_auto_dm_settings(email)
    raw_sheet = data.get('custom_sheet_id') or settings.get('custom_sheet_id') or None
    if raw_sheet and '/d/' in str(raw_sheet):
        raw_sheet = str(raw_sheet).split('/d/')[1].split('/')[0].split('?')[0].strip()
    sheet_id = raw_sheet or None

    if not sheet_id:
        return jsonify({
            "success": False,
            "message": "Silakan tempelkan dan simpan Link Google Spreadsheet milik Anda terlebih dahulu."
        }), 400

    ok, msg = db.db_ensure_ig_auto_dm_worksheet_template(email, sheet_id=sheet_id)
    rules = db.db_get_ig_auto_dm_rules_from_sheet(email, sheet_id=sheet_id) if ok else []

    return jsonify({
        "success": ok,
        "message": msg,
        "rules_count": len(rules),
        "rules": rules
    })

@ig_auto_dm_bp.route('/api/instagram-auto-dm/sync-sheet', methods=['POST'])
def sync_ig_auto_dm_sheet():
    """
    Sinkronisasi manual untuk memverifikasi dan menarik data aturan terbaru dari Google Spreadsheet user.
    """
    session_email = session.get('user_email', '').strip().lower()
    data = request.json or {}
    email = session_email or data.get('email', '').strip().lower() or "deripernandi99@gmail.com"

    settings = db.db_get_ig_auto_dm_settings(email)
    raw_sheet = data.get('custom_sheet_id') or settings.get('custom_sheet_id') or None
    if raw_sheet and '/d/' in str(raw_sheet):
        raw_sheet = str(raw_sheet).split('/d/')[1].split('/')[0].split('?')[0].strip()
    sheet_id = raw_sheet or None

    if not sheet_id:
        return jsonify({
            "success": False,
            "message": "Belum ada Google Spreadsheet yang ditautkan. Silakan masukkan link spreadsheet Anda terlebih dahulu.",
            "count": 0,
            "rules": []
        }), 400

    rules = db.db_get_ig_auto_dm_rules_from_sheet(email, sheet_id=sheet_id)
    return jsonify({
        "success": True,
        "message": f"Berhasil membaca {len(rules)} aturan aktif dari Google Spreadsheet Anda!",
        "count": len(rules),
        "rules": rules
    })

@ig_auto_dm_bp.route('/api/instagram-auto-dm/test-trigger', methods=['POST'])
def test_ig_auto_dm_trigger():
    """
    Simulator Uji Coba: Menguji teks komentar dan melihat apakah cocok dengan aturan
    (baik dari Dashboard atau Spreadsheet), lalu menampilkan preview respon balasan komentar & DM.
    """
    session_email = session.get('user_email', '').strip().lower()
    data = request.json or {}
    email = session_email or data.get('email', '').strip().lower() or "deripernandi99@gmail.com"
    comment_text = (data.get('comment_text') or '').strip()

    if not comment_text:
        return jsonify({"success": False, "message": "Teks komentar simulasi tidak boleh kosong."}), 400

    settings = db.db_get_ig_auto_dm_settings(email)
    source_mode = settings.get('source_mode', 'dashboard')

    if source_mode == 'spreadsheet':
        rules = db.db_get_ig_auto_dm_rules_from_sheet(email, sheet_id=settings.get('custom_sheet_id'))
    else:
        rules = settings.get('rules', [])

    matched_rule = None
    clean_text = comment_text.lower()
    for r in rules:
        if not r.get('is_active', True):
            continue
        kw = str(r.get('keyword', '')).strip().lower()
        if not kw:
            continue
        m_type = str(r.get('match_type', 'contains')).lower()

        if kw in ['*', 'all', 'semua']:
            matched_rule = r
            break
        elif m_type == 'exact':
            if clean_text == kw:
                matched_rule = r
                break
        else: # contains
            if kw in clean_text:
                matched_rule = r
                break

    if not matched_rule:
        return jsonify({
            "success": True,
            "matched": False,
            "source_mode": source_mode,
            "message": f"Komentar '{comment_text}' tidak cocok dengan kata kunci apapun di mode {source_mode.upper()}."
        })

    sample_user = data.get('sample_username') or "budi_kreator"
    dm_preview = matched_rule.get('dm_reply', '').replace('{username}', f"@{sample_user}")
    comm_preview = matched_rule.get('comment_reply', '').replace('{username}', f"@{sample_user}")

    return jsonify({
        "success": True,
        "matched": True,
        "source_mode": source_mode,
        "keyword": matched_rule.get('keyword'),
        "match_type": matched_rule.get('match_type', 'contains'),
        "comment_reply_preview": comm_preview,
        "dm_reply_preview": dm_preview,
        "rule_source": matched_rule.get('source', 'dashboard')
    })

