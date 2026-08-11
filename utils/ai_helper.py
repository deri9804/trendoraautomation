import os
import sys

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import config

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

def get_ai_chat_response(prompt):
    """
    Menghasilkan respon pesan dari Google Gemini AI dengan fallback aman jika API Key / Paket tidak tersedia.
    """
    if not prompt or not str(prompt).strip():
        return "Halo! Ada yang bisa saya bantu terkait otomatisasi TRENDORA?"

    if not HAS_GEMINI or not config.GEMINI_API_KEY:
        return f"Terima kasih atas pesan Anda: '{prompt}'. Asisten AI TRENDORA siap membantu proses otomatisasi konten dan workflow Anda!"

    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            f"Anda adalah asisten virtual resmi TRENDORA AUTOMATION. Jawab dengan ramah, lugas, dan profesional dalam Bahasa Indonesia.\n\nPertanyaan User: {prompt}"
        )
        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
        return "Maaf, AI saat ini belum dapat memberikan jawaban. Silakan coba beberapa saat lagi."
    except Exception as e:
        print(f"[AI Helper Error]: {e}")
        return f"Halo! Terima kasih telah menghubungi TRENDORA. Mengenai '{prompt}', sistem otomatisasi kami siap membantu meningkatkan jangkauan media sosial Anda."