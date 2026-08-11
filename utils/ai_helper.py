import os
import config

try:
    import google.generativeai as genai
    HAS_GEMINI = True
    if config.GEMINI_API_KEY:
        genai.configure(api_key=config.GEMINI_API_KEY)
except ImportError:
    HAS_GEMINI = False

def get_ai_chat_response(pesan_user):
    """Memproses balasan AI Customer Service Trendora AI dengan ketersediaan model otomatis."""
    if not HAS_GEMINI or not config.GEMINI_API_KEY:
        return "Maaf kak, sistem AI sedang offline karena API Key Gemini belum dikonfigurasi di server."
    
    system_instruction = """
    Kamu adalah "Trendora AI", Customer Service resmi dari platform TRENDORA AUTOMATION.
    Trendora adalah web layanan API automasi yang menghubungkan n8n ke berbagai sosial media (TikTok, YouTube, FB, IG, LinkedIn, Twitter, Threads) secara otomatis (Direct Post).
    Harga paket: 
    - Starter: Rp 150.000/bulan
    - Creator: Rp 200.000/bulan (paling laris)
    - Agency: Rp 250.000/bulan.
    Ada free trial 7 hari tapi API Key akan terkunci (hanya view-only). Untuk unlock API Key, harus berlangganan.
    
    Aturan menjawab:
    1. Jawab dengan ramah, profesional, tapi santai khas startup Indonesia (gunakan sapaan 'Kak' atau 'Kamu').
    2. Jika ditanya cara kerja: Jawab bahwa user cukup install 'n8n-nodes-automedia' di n8n, masukkan API key, lalu kirim webhook. Trendora yang urus upload videonya.
    3. Jika ditanya pertanyaan teknis di luar Trendora, arahkan sopan untuk kembali membahas automasi sosmed.
    4. Jawablah sesingkat dan sejelas mungkin, jangan terlalu panjang.
    5. Gunakan format markdown dasar jika perlu (bold, list).
    """
    
    try:
        valid_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                clean_name = m.name.replace('models/', '')
                valid_models.append(clean_name)
        
        if not valid_models:
            return "Waduh kak, API Key valid tapi sayangnya belum ada model AI yang terbuka di akun ini."
        
        preferred_order = []
        for m in valid_models:
            if '1.5-flash' in m: preferred_order.append(m)
        for m in valid_models:
            if '1.5-pro' in m and m not in preferred_order: preferred_order.append(m)
        for m in valid_models:
            if '2.5' not in m and m not in preferred_order: preferred_order.append(m)
        for m in valid_models:
            if m not in preferred_order: preferred_order.append(m)
        
        prompt_gabungan = f"INSTRUKSI SISTEM UNTUKMU (PENTING):\n{system_instruction}\n\n---\n\nPERTANYAAN PENGGUNA:\n{pesan_user}"
        
        for model_name in preferred_order:
            try:
                model = genai.GenerativeModel(model_name=model_name)
                response = model.generate_content(prompt_gabungan)
                return response.text
            except Exception as e:
                continue
        
        return "Maaf kak, saat ini antrean AI Customer Service kami sedang penuh (Sistem Overload). Mohon tunggu beberapa saat lagi atau tinggalkan pesan melalui halaman **Kontak** ya! 🙏\n\n*(Info Developer: Limit harian API Key Gemini telah habis, silakan ganti API Key di Vercel)*"
        
    except Exception as e:
        return f"Error Sistem Internal: {str(e)}"