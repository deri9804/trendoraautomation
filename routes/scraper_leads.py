import os
import re
import json
import html
import base64
import urllib.request
import urllib.parse
from datetime import datetime
from flask import Blueprint, request, jsonify

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
    
    # Pattern tambahan jika ada wa.me/628xxx
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
        if m and m.group(1) not in ['p', 'reel', 'explore', 'stories', 'tv']:
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
        if m and m.group(1) not in ['sharer', 'pages', 'groups', 'events', 'watch']:
            return m.group(1)
    return ""

# =========================================================================
# CORE SEARCH & SCRAPING WORKERS
# =========================================================================

def execute_web_search(query, count=10):
    """
    Melakukan pencarian ke Bing Search engine dengan headers browser resmi
    dan mengekstrak data judul, URL tujuan, dan snippet ringkasan.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded}&count={count}"
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
                    "snippet": snippet
                })
    except Exception as e:
        print(f"[Lead Scraper Search Error]: {e}")
        
    return items

def search_nominatim_places(keyword, location="", limit=10):
    """
    Mencari entitas bisnis / tempat lokal melalui OpenStreetMap Nominatim.
    Menghasilkan data akurat nama bisnis, alamat jalan, kota, dan koordinat.
    """
    full_q = f"{keyword} {location}".strip()
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(full_q)}&format=json&addressdetails=1&extratags=1&limit={limit}"
    headers = {
        'User-Agent': 'TrendoraAutomation-LeadFinder/1.0 (contact: info@trendoraautomation.my.id)'
    }
    req = urllib.request.Request(url, headers=headers)
    places = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for d in data:
                addr = d.get('address', {})
                street = addr.get('road') or addr.get('suburb') or addr.get('neighbourhood') or ''
                city = addr.get('city') or addr.get('town') or addr.get('municipality') or addr.get('county') or ''
                state = addr.get('state') or ''
                full_address = d.get('display_name', '')
                
                extra = d.get('extratags', {}) or {}
                raw_phone = extra.get('phone') or extra.get('contact:phone') or extra.get('contact:whatsapp') or ''
                website = extra.get('website') or extra.get('contact:website') or ''
                
                phones = extract_phones_from_text(raw_phone)
                primary_phone = phones[0] if phones else ""
                
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
    except Exception as e:
        print(f"[Nominatim Place Search Error]: {e}")
        
    return places

def scrape_leads_by_platform(keyword, location="", platform="instagram", limit=10):
    """
    Men-scrape leads khusus untuk satu platform tertentu (Instagram, TikTok, Facebook, YouTube, Google Maps, Web).
    """
    loc_part = f'"{location}"' if location else ''
    
    # Siapkan pola dorking cerdas berdasarkan target platform
    if platform == 'instagram':
        query = f'site:instagram.com "{keyword}" {loc_part} ("08" OR "wa.me" OR "+62")'
    elif platform == 'tiktok':
        query = f'site:tiktok.com/@ "{keyword}" {loc_part} ("08" OR "wa.me" OR "wa")'
    elif platform == 'facebook':
        query = f'site:facebook.com "{keyword}" {loc_part} ("08" OR "hubungi" OR "+62")'
    elif platform == 'youtube':
        query = f'site:youtube.com/@ "{keyword}" {loc_part} ("08" OR "+62" OR "@gmail.com")'
    elif platform == 'google_maps':
        query = f'site:google.com/maps/place "{keyword}" {loc_part} ("08" OR "+62")'
    else:
        query = f'"{keyword}" {loc_part} ("08" OR "wa.me" OR "+62")'
        
    raw_results = execute_web_search(query, count=limit * 2)
    
    # Jika platform adalah google_maps dan hasil web search sedikit, gabungkan dengan Nominatim
    leads = []
    seen_identifiers = set()
    
    if platform == 'google_maps':
        nomi_places = search_nominatim_places(keyword, location=location, limit=limit)
        for p in nomi_places:
            if p['title'] not in seen_identifiers:
                seen_identifiers.add(p['title'])
                leads.append(p)
                
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
            "source": f"search_{platform}"
        })
        
        if len(leads) >= limit:
            break
            
    return leads

# =========================================================================
# API ENDPOINTS FOR N8N INTEGRATION
# =========================================================================

@scraper_bp.route('/api/scraper/leads', methods=['POST', 'GET'])
def api_scrape_leads():
    """
    ENDPOINT UTAMA: Omnichannel Lead Scraper untuk n8n.
    Mendukung scraping simultan ke Google Maps, Instagram, TikTok, Facebook, YouTube, & Web Dorking.
    
    Payload JSON (POST) atau Query Params (GET):
    {
      "keyword": "klinik kecantikan",
      "location": "Jakarta",
      "platforms": ["google_maps", "instagram", "tiktok", "facebook", "youtube"],
      "limit_per_platform": 10
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    keyword = (data.get('keyword') or request.args.get('keyword') or '').strip()
    location = (data.get('location') or request.args.get('location') or '').strip()
    
    if not keyword:
        return jsonify({
            "success": False,
            "message": "Parameter 'keyword' wajib diisi (contoh: 'coffee shop', 'klinik kecantikan', 'distributor gamis')."
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
    
    all_leads = []
    seen_keys = set()
    summary_counts = {}
    
    for plat in platforms:
        plat_leads = scrape_leads_by_platform(keyword, location=location, platform=plat, limit=limit_per_platform)
        summary_counts[plat] = len(plat_leads)
        for lead in plat_leads:
            # Deduplikasi berdasarkan primary_phone atau url
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
            "limit_per_platform": limit_per_platform
        },
        "total_leads": len(all_leads),
        "platform_summary": summary_counts,
        "leads": all_leads,
        "timestamp": datetime.now().isoformat()
    }), 200

@scraper_bp.route('/api/scraper/google-maps', methods=['POST', 'GET'])
def api_scrape_google_maps():
    """Endpoint spesifik untuk Google Maps / Bisnis Lokal B2B."""
    data = request.get_json(force=True, silent=True) or {}
    keyword = (data.get('keyword') or request.args.get('keyword') or '').strip()
    location = (data.get('location') or request.args.get('location') or '').strip()
    limit = int(data.get('limit') or request.args.get('limit') or 15)
    
    if not keyword:
        return jsonify({"success": False, "message": "Parameter 'keyword' diperlukan."}), 400
        
    leads = scrape_leads_by_platform(keyword, location=location, platform="google_maps", limit=limit)
    return jsonify({
        "success": True,
        "keyword": keyword,
        "location": location,
        "total": len(leads),
        "leads": leads
    }), 200

@scraper_bp.route('/api/scraper/social', methods=['POST', 'GET'])
def api_scrape_social():
    """Endpoint spesifik media sosial (Instagram, TikTok, Facebook, YouTube)."""
    data = request.get_json(force=True, silent=True) or {}
    keyword = (data.get('keyword') or request.args.get('keyword') or '').strip()
    location = (data.get('location') or request.args.get('location') or '').strip()
    platform = (data.get('platform') or request.args.get('platform') or 'instagram').strip().lower()
    limit = int(data.get('limit') or request.args.get('limit') or 15)
    
    if not keyword:
        return jsonify({"success": False, "message": "Parameter 'keyword' diperlukan."}), 400
        
    leads = scrape_leads_by_platform(keyword, location=location, platform=platform, limit=limit)
    return jsonify({
        "success": True,
        "platform": platform,
        "keyword": keyword,
        "location": location,
        "total": len(leads),
        "leads": leads
    }), 200
