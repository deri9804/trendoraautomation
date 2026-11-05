import os
import re
import json
import html
import base64
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from flask import Blueprint, request, jsonify

try:
    from dotenv import load_dotenv
    # Pastikan .env dimuat dari direktori root proyek
    _basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    load_dotenv(os.path.join(_basedir, '.env'), override=True)
except Exception:
    pass

scraper_bp = Blueprint('scraper_leads', __name__)

# =========================================================================
# HELPER UTILITIES: PHONE, EMAIL, & URL SANITIZERS
# =========================================================================

def sanitize_phone_to_wa(raw_phone):
    """
    Mengubah variasi nomor telepon Indonesia (+62 812-..., 0812..., 62812...)
    menjadi format standar WhatsApp: 628xxxxxxxxxx (hanya angka).
    """
    if not raw_phone:
        return None
    digits = re.sub(r'\D', '', str(raw_phone))
    if digits.startswith('62'):
        formatted = digits
    elif digits.startswith('0'):
        formatted = '62' + digits[1:]
    elif digits.startswith('8'):
        formatted = '62' + digits
    else:
        formatted = digits
    
    # Validasi panjang nomor HP Indonesia (biasanya 10 - 15 digit)
    if 10 <= len(formatted) <= 15 and formatted.startswith('628'):
        return formatted
    return None

def extract_phones_from_text(text):
    """Mengekstrak dan menormalkan semua nomor HP/WhatsApp Indonesia dari teks."""
    if not text:
        return []
    # Pattern mencakup: 08xx-xxxx-xxxx, +628xxxx, 628xxxx, wa.me/628xxx
    pattern = re.compile(r'(?:(?:\+?62)|0)8[0-9]{1,2}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,5}')
    matches = pattern.findall(text)
    
    # Pattern tambahan jika ada wa.me/628xxx atau wa.me/08xxx
    wa_matches = re.findall(r'wa\.me/(?:(?:\+?62)|0)?(8[0-9]{8,12})', text, re.IGNORECASE)
    for w in wa_matches:
        matches.append('62' + w)
        
    results = []
    for m in matches:
        clean = sanitize_phone_to_wa(m)
        if clean and clean not in results:
            results.append(clean)
    return results

def extract_emails_from_text(text):
    """Mengekstrak alamat email dari teks dan membuang ekstensi gambar/sampah."""
    if not text:
        return []
    pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    matches = pattern.findall(text)
    clean = []
    ignored_exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')
    for m in matches:
        em = m.lower().strip('.')
        if not em.endswith(ignored_exts) and em not in clean:
            clean.append(em)
    return clean

def decode_bing_url(bing_url):
    """Mendekode link redirect Bing menjadi URL target asli."""
    clean = html.unescape(bing_url)
    m = re.search(r'[?&]u=a1([a-zA-Z0-9_-]+)', clean)
    if m:
        b64 = m.group(1)
        b64 += '=' * ((4 - len(b64) % 4) % 4)
        try:
            return base64.urlsafe_b64decode(b64).decode('utf-8', errors='ignore')
        except Exception:
            pass
    return clean

def extract_social_handle(url, platform):
    """Mengekstrak username atau nama halaman dari URL media sosial."""
    if not url:
        return ""
    if platform == 'instagram':
        m = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)', url)
        if m and m.group(1) not in ['p', 'reel', 'explore', 'stories', 'tv', 'about', 'developer']:
            return f"@{m.group(1)}"
    elif platform == 'tiktok':
        m = re.search(r'tiktok\.com/@([a-zA-Z0-9_.]+)', url)
        if m:
            return f"@{m.group(1)}"
    elif platform == 'youtube':
        m = re.search(r'youtube\.com/@([a-zA-Z0-9_.-]+)', url)
        if m:
            return f"@{m.group(1)}"
        m_ch = re.search(r'youtube\.com/channel/([a-zA-Z0-9_.-]+)', url)
        if m_ch:
            return m_ch.group(1)
    elif platform == 'facebook':
        m = re.search(r'facebook\.com/([a-zA-Z0-9_.-]+)', url)
        if m and m.group(1) not in ['sharer', 'pages', 'groups', 'events', 'watch', 'login', 'recover']:
            return m.group(1)
    return ""

# =========================================================================
# SEARCH ENGINES: GOOGLE CSE (OPSI A), SERPER, & BING FALLBACK
# =========================================================================

def search_google_cse(query, api_key, cx, count=10):
    """
    OPSI A: Google Custom Search JSON API (Official & 100% Anti-Banned).
    Mendapatkan data bio profil, link, dan kontak WhatsApp langsung dari indeks Google.
    Mengembalikan: (items, debug_status)
    """
    if not api_key or not cx:
        return [], "Missing API Key or CX"
    
    count = min(max(count, 1), 10)
    params = {
        'key': api_key.strip(),
        'cx': cx.strip(),
        'q': query.strip(),
        'num': count,
        'gl': 'id',
        'hl': 'id'
    }
    url = f"https://www.googleapis.com/customsearch/v1?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'TrendoraLeadScraper/1.0'})
    
    items = []
    debug_status = "OK"
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            raw_items = data.get('items', [])
            debug_status = f"Google CSE OK: found {len(raw_items)} items for query: {query}"
            for it in raw_items:
                title = it.get('title', '')
                link = it.get('link', '')
                snippet = it.get('snippet', '')
                
                # Cek metadata og:description jika tersedia
                pagemap = it.get('pagemap', {}) or {}
                metas = pagemap.get('metatags', [{}])[0] if pagemap.get('metatags') else {}
                og_desc = metas.get('og:description', '')
                full_snippet = f"{snippet} {og_desc}".strip()
                
                items.append({
                    "title": title,
                    "url": link,
                    "snippet": full_snippet,
                    "engine": "google_cse"
                })
    except urllib.error.HTTPError as e:
        err_text = e.read().decode('utf-8', errors='ignore')
        try:
            err_json = json.loads(err_text)
            err_msg = err_json.get('error', {}).get('message', err_text[:120])
        except Exception:
            err_msg = err_text[:120]
        debug_status = f"Google CSE HTTP Error {e.code}: {err_msg}"
        print(f"[Google CSE Error]: {debug_status}")
    except Exception as e:
        debug_status = f"Google CSE Exception: {str(e)}"
        print(f"[Google CSE Error]: {debug_status}")
        
    return items, debug_status

def search_serper(query, api_key, count=10):
    """Pencarian Google via Serper.dev API."""
    if not api_key:
        return []
    
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "num": count,
        "gl": "id",
        "hl": "id"
    }).encode('utf-8')
    
    headers = {
        'X-API-KEY': api_key.strip(),
        'Content-Type': 'application/json'
    }
    req = urllib.request.Request(url, data=payload, headers=headers)
    items = []
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for it in data.get('organic', []):
                items.append({
                    "title": it.get('title', ''),
                    "url": it.get('link', ''),
                    "snippet": it.get('snippet', ''),
                    "engine": "serper"
                })
    except Exception as e:
        print(f"[Serper Error]: {e}")
    return items

def execute_web_search(query, count=10):
    """
    Fallback web search gratis via Bing dengan normalisasi query & scraping HTML.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8'
    }
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded}&count={count}&setlang=id-ID&cc=ID"
    req = urllib.request.Request(url, headers=headers)
    
    items = []
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            parts = content.split('class="b_algo"')
            for part in parts[1:]:
                h2_m = re.search(r'<h2><a[^>]+href="([^"]+)"[^>]*>(.*?)</a></h2>', part, re.DOTALL)
                if not h2_m:
                    continue
                
                raw_url = h2_m.group(1)
                raw_title = h2_m.group(2)
                title = re.sub(r'<[^>]+>', '', raw_title).strip()
                dest_url = decode_bing_url(raw_url)
                
                snippet = ""
                snip_m = re.search(r'<div class="b_caption"[^>]*><p[^>]*>(.*?)</p>', part, re.DOTALL)
                if snip_m:
                    snippet = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip()
                else:
                    p_m = re.search(r'<p[^>]*>(.*?)</p>', part, re.DOTALL)
                    if p_m:
                        snippet = re.sub(r'<[^>]+>', '', p_m.group(1)).strip()
                
                items.append({
                    "title": title,
                    "url": dest_url,
                    "snippet": snippet,
                    "engine": "bing"
                })
    except Exception as e:
        print(f"[Lead Scraper Search Error]: {e}")
        
    return items

def search_nominatim_places(keyword, location="", limit=10, only_with_phone=False):
    """
    Mencari entitas bisnis / tempat lokal melalui OpenStreetMap Nominatim.
    """
    full_q = f"{keyword} {location}".strip()
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(full_q)}&format=json&addressdetails=1&extratags=1&limit={limit * 2}"
    headers = {
        'User-Agent': 'TrendoraAutomation-LeadFinder/1.1 (contact: info@trendoraautomation.my.id)'
    }
    req = urllib.request.Request(url, headers=headers)
    places = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for d in data:
                addr = d.get('address', {})
                city = addr.get('city') or addr.get('town') or addr.get('municipality') or addr.get('county') or ''
                state = addr.get('state') or ''
                full_address = d.get('display_name', '')
                
                extra = d.get('extratags', {}) or {}
                raw_phone = extra.get('phone') or extra.get('contact:phone') or extra.get('contact:whatsapp') or ''
                website = extra.get('website') or extra.get('contact:website') or ''
                
                phones = extract_phones_from_text(raw_phone)
                primary_phone = phones[0] if phones else ""
                
                # Jika only_with_phone aktif, skip tempat yang tidak punya nomor telepon
                if only_with_phone and not primary_phone:
                    continue
                
                places.append({
                    "title": d.get('name') or full_address.split(',')[0],
                    "platform": "google_maps",
                    "category": d.get('type') or d.get('class') or keyword,
                    "username": "",
                    "url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(full_address)}",
                    "snippet": full_address,
                    "address": full_address,
                    "city": city,
                    "state": state,
                    "latitude": d.get('lat'),
                    "longitude": d.get('lon'),
                    "phones": phones,
                    "primary_phone": primary_phone,
                    "whatsapp_url": f"https://wa.me/{primary_phone}" if primary_phone else "",
                    "emails": [],
                    "primary_email": "",
                    "website": website,
                    "source": "openstreetmap_nominatim"
                })
                if len(places) >= limit:
                    break
    except Exception as e:
        print(f"[Nominatim Place Search Error]: {e}")
        
    return places

def scrape_leads_by_platform(keyword, location="", platform="instagram", limit=10, google_api_key="", google_cse_cx="", serper_api_key="", only_with_phone=False):
    """
    Men-scrape leads khusus untuk satu platform tertentu.
    Mendukung Google CSE (Opsi A), Serper, dan multi-fallback.
    Mengembalikan: (leads, debug_info)
    """
    loc_part = f"{location}" if location else ''
    is_google_cse = bool(google_api_key and google_cse_cx)
    
    # 1. Format Query Pencarian:
    # Dork query spesifik platform untuk Google (Serper) & Web Search
    if platform == 'instagram':
        dork_query = f'site:instagram.com {keyword} {loc_part} (wa OR "08" OR whatsapp)'
    elif platform == 'tiktok':
        dork_query = f'site:tiktok.com/@ {keyword} {loc_part} (wa OR "08" OR whatsapp)'
    elif platform == 'facebook':
        dork_query = f'site:facebook.com {keyword} {loc_part} (wa OR "08" OR whatsapp)'
    elif platform == 'youtube':
        dork_query = f'site:youtube.com/@ {keyword} {loc_part} (wa OR "08" OR whatsapp)'
    elif platform == 'google_maps':
        dork_query = f'site:google.com/maps {keyword} {loc_part} ("08" OR "+62")'
    else:
        dork_query = f'{keyword} {loc_part} (wa OR "08" OR whatsapp)'
        
    cse_query = f'{keyword} {loc_part} wa OR "08" OR whatsapp'
        
    leads = []
    seen_identifiers = set()
    debug_info = ""
    
    # Khusus Google Maps: Ambil juga dari OpenStreetMap Nominatim
    if platform == 'google_maps':
        nomi_places = search_nominatim_places(keyword, location=location, limit=limit, only_with_phone=only_with_phone)
        for p in nomi_places:
            if p['title'] not in seen_identifiers:
                seen_identifiers.add(p['title'])
                leads.append(p)
                
    # 2. Eksekusi Pencarian Menggunakan Engine Terbaik
    raw_results = []
    
    # Prioritas 1: Serper.dev jika dikonfigurasi (Google Search Live 100% Anti-Banned & Tanpa Batas CSE)
    if serper_api_key:
        serper_results = search_serper(dork_query, serper_api_key, count=limit)
        if serper_results:
            raw_results = serper_results
            debug_info = f"Serper Google Search OK: found {len(raw_results)} items"
            
    # Prioritas 2: Google Custom Search Engine (Opsi A) jika Serper belum ada
    if not raw_results and is_google_cse:
        raw_results, cse_debug = search_google_cse(cse_query, google_api_key, google_cse_cx, count=limit)
        debug_info = cse_debug
        
    # Prioritas 3: Fallback ke Web Search Engine jika kedua API di atas belum mengembalikan hasil
    if not raw_results:
        raw_results = execute_web_search(dork_query, count=limit * 2)
        debug_info = f"{debug_info} | Web fallback: {len(raw_results)} items" if debug_info else f"Web dorking: {len(raw_results)} items"
        
    for item in raw_results:
        title = item.get('title', '')
        dest_url = item.get('url', '')
        snippet = item.get('snippet', '')
        combined = f"{title} {snippet} {dest_url}"
        
        # Validasi domain relevan untuk platform
        if platform == 'instagram' and 'instagram.com' not in dest_url:
            continue
        elif platform == 'tiktok' and 'tiktok.com' not in dest_url:
            continue
        elif platform == 'facebook' and 'facebook.com' not in dest_url:
            continue
        elif platform == 'youtube' and ('youtube.com' not in dest_url and 'youtu.be' not in dest_url):
            continue
            
        phones = extract_phones_from_text(combined)
        emails = extract_emails_from_text(combined)
        username = extract_social_handle(dest_url, platform)
        primary_phone = phones[0] if phones else ""
        
        # Jika mode only_with_phone aktif, skip prospek yang tidak punya WA
        if only_with_phone and not primary_phone:
            continue
        
        identifier = primary_phone or dest_url
        if identifier in seen_identifiers:
            continue
        seen_identifiers.add(identifier)
        
        leads.append({
            "title": title,
            "platform": platform,
            "category": keyword,
            "username": username,
            "url": dest_url,
            "snippet": snippet,
            "address": location if location else "",
            "city": location if location else "",
            "phones": phones,
            "primary_phone": primary_phone,
            "whatsapp_url": f"https://wa.me/{primary_phone}" if primary_phone else "",
            "emails": emails,
            "primary_email": emails[0] if emails else "",
            "website": dest_url if platform not in ['instagram', 'tiktok', 'facebook', 'youtube'] else "",
            "source": f"google_search_{platform}" if item.get('engine') == 'google_cse' else f"search_{platform}"
        })
        
        if len(leads) >= limit:
            break
            
    return leads, debug_info

# =========================================================================
# API ENDPOINT FOR N8N INTEGRATION
# =========================================================================

@scraper_bp.route('/api/scraper/leads', methods=['POST', 'GET'])
def api_scrape_leads():
    """
    ENDPOINT UTAMA: Omnichannel Lead Scraper untuk n8n.
    Mendukung scraping Google CSE (Opsi A), Google Maps, Instagram, TikTok, Facebook, YouTube.
    """
    data = request.get_json(force=True, silent=True) or {}
    keyword = (data.get('keyword') or request.args.get('keyword') or '').strip()
    location = (data.get('location') or request.args.get('location') or '').strip()
    
    if not keyword:
        return jsonify({
            "success": False,
            "message": "Parameter 'keyword' wajib diisi (contoh: 'trader forex', 'klinik kecantikan', 'kuliner lampung')."
        }), 400
        
    raw_platforms = data.get('platforms') or request.args.get('platforms')
    if isinstance(raw_platforms, str):
        platforms = [p.strip().lower() for p in raw_platforms.split(',') if p.strip()]
    elif isinstance(raw_platforms, list):
        platforms = [str(p).strip().lower() for p in raw_platforms]
    else:
        platforms = ["google_maps", "instagram", "tiktok", "facebook", "youtube"]
        
    try:
        limit_per_platform = int(data.get('limit_per_platform') or request.args.get('limit_per_platform') or 10)
    except (ValueError, TypeError):
        limit_per_platform = 10
    limit_per_platform = max(1, min(limit_per_platform, 30))
    
    # Ambil konfigurasi API Search: Prioritas Serper.dev, baru Google CSE
    serper_api_key = (
        data.get('serper_api_key') or
        request.args.get('serper_api_key') or
        os.environ.get('SERPER_API_KEY') or ''
    ).strip()
    
    google_api_key = (
        data.get('google_api_key') or
        request.args.get('google_api_key') or
        os.environ.get('GOOGLE_SEARCH_API_KEY') or ''
    ).strip()
    
    google_cse_cx = (
        data.get('google_cse_cx') or
        request.args.get('google_cse_cx') or
        os.environ.get('GOOGLE_SEARCH_ENGINE_ID') or
        os.environ.get('GOOGLE_CSE_CX') or ''
    ).strip()
    
    # Parameter apakah hanya mengembalikan lead yang punya nomor WhatsApp
    raw_only_phone = data.get('only_with_phone') or request.args.get('only_with_phone')
    if raw_only_phone is not None:
        only_with_phone = str(raw_only_phone).lower() in ['true', '1', 'yes']
    else:
        only_with_phone = False
    
    all_leads = []
    seen_keys = set()
    summary_counts = {}
    debug_per_platform = {}
    
    for plat in platforms:
        plat_leads, p_debug = scrape_leads_by_platform(
            keyword,
            location=location,
            platform=plat,
            limit=limit_per_platform,
            google_api_key=google_api_key,
            google_cse_cx=google_cse_cx,
            serper_api_key=serper_api_key,
            only_with_phone=only_with_phone
        )
        summary_counts[plat] = len(plat_leads)
        debug_per_platform[plat] = p_debug
        for lead in plat_leads:
            dedup_key = lead.get('primary_phone') or lead.get('url')
            if dedup_key and dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                all_leads.append(lead)
                
    return jsonify({
        "success": True,
        "query": {
            "keyword": keyword,
            "location": location,
            "platforms": platforms,
            "limit_per_platform": limit_per_platform,
            "engine_used": "serper" if serper_api_key else ("google_cse" if (google_api_key and google_cse_cx) else "web_dorking"),
            "only_with_phone": only_with_phone
        },
        "total_leads": len(all_leads),
        "platform_summary": summary_counts,
        "debug_info": debug_per_platform,
        "leads": all_leads,
        "timestamp": datetime.now().isoformat()
    }), 200
