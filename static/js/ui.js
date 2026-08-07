var globalUserData = null;
var isKeyMasked = true;
var currentViewMode = 'landing';
var selectedPlanName = 'Creator Monthly';
var selectedPlanPrice = 'Rp.200.000/mo';
var lastSnapToken = localStorage.getItem('automedia_snap_token') || null;
var paymentPollingInterval = null;

const LEGAL_DOCUMENTS = {
  tos: `
    <h4>1. Penerimaan Syarat & Ketentuan</h4>
    <p>Dengan mengakses atau menggunakan layanan TRENDORA AUTOMATION, Anda menyetujui untuk terikat oleh Syarat dan Ketentuan ini. Anda harus berusia minimal 18 tahun atau memiliki izin hukum yang sah.</p>

    <h4>2. Deskripsi Layanan</h4>
    <p>TRENDORA menyediakan antarmuka API, community node (n8n/Make), serta perangkat lunak automasi untuk mempublikasikan konten media secara otomatis ke berbagai platform media sosial.</p>

    <h4>3. Pendaftaran Akun & Keamanan</h4>
    <p>Anda wajib memberikan informasi akurat dan bertanggung jawab penuh menjaga kerahasiaan kredensial login (OTP 2FA) dan API Key Anda. TRENDORA tidak bertanggung jawab atas kerugian akibat penyalahgunaan API Key.</p>

    <h4>4. Otorisasi Platform Pihak Ketiga (OAuth 2.0)</h4>
    <p>Layanan kami memerlukan otorisasi resmi ke akun Anda. Anda menyetujui Syarat Layanan dari masing-masing platform (TikTok, YouTube, Meta, dsb). Kami tidak berafiliasi resmi dengan entitas tersebut.</p>

    <h4>5. Penggunaan yang Diizinkan dan Dilarang</h4>
    <p>Anda <strong>dilarang keras</strong> menggunakan Layanan untuk spam, hoaks, perjudian, melanggar Hak Kekayaan Intelektual, melakukan Reverse Engineering, atau melanggar rate-limit API platform pihak ketiga.</p>

    <h4>6. Langganan, Pembayaran, dan Pembatalan</h4>
    <p>Pembayaran diproses via Midtrans. Tersedia free trial 7 hari. Berlaku garansi uang kembali 30 hari jika terjadi kegagalan sistem utama kami (Force Majeure).</p>

    <h4>7. Hak Kekayaan Intelektual</h4>
    <p>Infrastruktur dan kode API adalah milik TRENDORA. Anda tetap memegang hak cipta atas konten video Anda sendiri.</p>

    <h4>8. Batasan Tanggung Jawab</h4>
    <p>Layanan disediakan "As Is". Kami tidak bertanggung jawab atas akun media sosial Anda yang ditangguhkan (banned) akibat pelanggaran kebijakan konten di platform pihak ketiga.</p>

    <h4>9. Penghentian Layanan</h4>
    <p>Kami berhak menangguhkan akun Anda tanpa pemberitahuan jika terbukti melanggar Syarat, khususnya terkait Spamming masif.</p>

    <h4>10. Hukum yang Berlaku</h4>
    <p>Syarat ini diatur sesuai hukum Republik Indonesia. Perselisihan diselesaikan secara musyawarah atau melalui pengadilan Republik Indonesia.</p>
  `,
  privacy: `
    <h4>1. Informasi yang Kami Kumpulkan</h4>
    <p>Kami mengumpulkan Informasi Akun (nama, email, Secret 2FA), Data Otentikasi (Access & Refresh Token, kami TIDAK menyimpan password sosmed), Data Transaksi (via Midtrans), dan Log Aktivitas.</p>

    <h4>2. Penggunaan Informasi Data Anda</h4>
    <p>Data digunakan semata-mata untuk mengoperasikan fungsi automasi posting API, menyediakan dukungan pelanggan, serta mendeteksi dan mencegah spam/penyalahgunaan sistem.</p>

    <h4>3. Pengungkapan Kepada Pihak Ketiga</h4>
    <p>Kami <strong>tidak akan pernah</strong> menjual, menyewakan, atau memperdagangkan data Anda. Data hanya dibagikan ke penyedia server (cloud) terikat kerahasiaan atau jika diwajibkan oleh hukum.</p>

    <h4>4. Keamanan Data</h4>
    <p>Kami menerapkan enkripsi SSL/TLS (HTTPS) dan hashing satu arah. Kami berusaha maksimal menjaga data, namun tidak ada transmisi internet yang 100% aman mutlak.</p>

    <h4>5. Hak-Hak Pengguna</h4>
    <p>Anda berhak untuk mengakses, memperbarui, mencabut akses (Revoke OAuth) langsung dari dasbor, hingga meminta penghapusan permanen (Right to be Forgotten) akun Anda.</p>

    <h4>6. Retensi & Penyimpanan Data</h4>
    <p>Data disimpan selama akun aktif atau diperlukan untuk keperluan hukum. Log aktivitas lama dihapus secara berkala.</p>

    <h4>7. Kebijakan Anak-Anak (COPPA)</h4>
    <p>Layanan kami tidak ditujukan untuk anak di bawah usia 13 tahun. Kami tidak mengumpulkan data dari individu di bawah batasan umur secara sengaja.</p>

    <h4>8. Perubahan Kebijakan</h4>
    <p>Kami akan memberitahu Anda via email atau pengumuman dashboard sebelum perubahan signifikan pada kebijakan privasi berlaku efektif.</p>

    <h4>9. Hubungi Kami</h4>
    <p>Untuk pertanyaan privasi, hubungi: <strong>deripernandi99@gmail.com</strong>.</p>
  `
};

function openLegalModal(type) {
  const modal = document.getElementById('legalModalOverlay');
  const heading = document.getElementById('legalModalHeading');
  const badge = document.getElementById('legalBadgeTitle');
  const body = document.getElementById('legalModalBody');

  if (!modal || !body) return;

  if (type === 'privacy') {
    if (heading) heading.innerText = 'Kebijakan Privasi (Privacy Policy)';
    if (badge) badge.innerText = 'KEBIJAKAN PRIVASI';
    body.innerHTML = LEGAL_DOCUMENTS.privacy;
  } else {
    if (heading) heading.innerText = 'Syarat & Ketentuan Layanan (Terms of Service)';
    if (badge) badge.innerText = 'SYARAT & KETENTUAN';
    body.innerHTML = LEGAL_DOCUMENTS.tos;
  }

  modal.style.display = 'flex';
}

function closeLegalModal() {
  const modal = document.getElementById('legalModalOverlay');
  if (modal) modal.style.display = 'none';
}

function showDashboardPage() {
  if (window.location.pathname !== '/dashboard') {
    window.location.href = '/dashboard';
    return;
  }
}

function showLandingPage() {
  if (window.location.pathname !== '/') {
    window.location.href = '/';
    return;
  }
}

function scrollToPricing() {
  showLandingPage();
  setTimeout(() => {
    const pricingSection = document.getElementById('pricing');
    if (pricingSection) pricingSection.scrollIntoView({ behavior: 'smooth' });
  }, 100);
}

function scrollToDocs() {
  showLandingPage();
  setTimeout(() => {
    const docsSec = document.getElementById('n8n-docs');
    if (docsSec) docsSec.scrollIntoView({ behavior: 'smooth' });
  }, 100);
}

function openLoginModal() {
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

function openRegisterModal(planName = 'Creator Monthly', planPrice = 'Rp.200.000/mo') {
  localStorage.setItem('selectedPlanName', planName);
  localStorage.setItem('selectedPlanPrice', planPrice);
  if (window.location.pathname !== '/checkout') {
    window.location.href = '/checkout';
  }
}

function handleStartFree(planName = 'Creator Monthly', planPrice = 'Rp.200.000/mo') {
  openRegisterModal(planName, planPrice);
}

function closeApiModal() {
  if (window.location.pathname === '/login' || window.location.pathname === '/checkout') {
    window.location.href = '/';
  }
}

function showToast(message, color) {
  const toast = document.createElement('div');
  toast.style.cssText = 'position:fixed; bottom:20px; right:20px; background:#0f1524; color:#fff; border:1px solid ' + (color || '#ec4899') + '; padding:12px 20px; border-radius:10px; z-index:99999; font-size:13px; font-weight:600; box-shadow:0 10px 30px rgba(0,0,0,0.5);';
  toast.innerText = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function renderLoggedInUI(user, autoNavigateToDashboard = true) {
  const navGuest = document.getElementById('navGuestGroup');
  const navUser = document.getElementById('navUserGroup');
  const navName = document.getElementById('navUserName');
  const navDashLink = document.getElementById('navDashLink');

  if (navGuest) navGuest.style.display = 'none';
  if (navUser) navUser.style.display = 'flex';
  if (navName) navName.innerText = user.name || 'User';
  if (navDashLink) navDashLink.style.display = 'inline-block';

  const dashName = document.getElementById('dashName');
  const dashEmail = document.getElementById('dashUserEmail');
  const dashStatus = document.getElementById('dashAccountStatus');
  const btnDashUpgrade = document.getElementById('btnDashUpgrade'); 

  if (dashName) dashName.innerText = user.name || 'User';
  if (dashEmail) dashEmail.innerText = user.email || '-';
  
  if (dashStatus) {
    dashStatus.innerText = user.status || 'Active (7-Day Free Trial)';
    
    if (user.isPaid) {
      dashStatus.style.color = '#34d399';
      if (btnDashUpgrade) btnDashUpgrade.style.display = 'none'; 
    } else if (user.apiKey && user.apiKey !== '-') {
      dashStatus.style.color = '#f87171';
      if (btnDashUpgrade) btnDashUpgrade.style.display = 'inline-block';
    } else {
      dashStatus.style.color = '#f59e0b';
      if (btnDashUpgrade) btnDashUpgrade.style.display = 'inline-block';
    }
  }

  if (typeof updateDashApiKeyDisplay === 'function') updateDashApiKeyDisplay(user.apiKey || '-');
  if (typeof loadWebhookUrl === 'function') loadWebhookUrl();
  if (typeof loadUserPostLogs === 'function') loadUserPostLogs();
  
  if (typeof renderSocialConnectionsUI === 'function') renderSocialConnectionsUI();
}

function toggleFaq(element) {
  const parentItem = element.parentElement;
  const icon = element.querySelector('.faq-icon');
  
  if (parentItem.classList.contains('active')) {
    parentItem.classList.remove('active');
    if (icon) icon.innerHTML = '&plus;';
  } else {
    document.querySelectorAll('.faq-item').forEach(item => {
      item.classList.remove('active');
      const itemIcon = item.querySelector('.faq-icon');
      if (itemIcon) itemIcon.innerHTML = '&plus;';
    });
    parentItem.classList.add('active');
    if (icon) icon.innerHTML = '&minus;';
  }
}

// ==========================================
// LOGIKA CHAT WIDGET AI (Nembak ke Flask/Gemini)
// ==========================================
function toggleChat() {
  const chatWindow = document.getElementById('chatWindow');
  const toggleBtn = document.getElementById('chatToggleBtn');
  
  if (chatWindow.style.display === 'none' || chatWindow.style.display === '') {
    chatWindow.style.display = 'flex';
    toggleBtn.innerHTML = '<span class="chat-icon" style="font-size:24px;">✖</span>';
    
    setTimeout(() => {
      document.getElementById('chatInput').focus();
    }, 100);
  } else {
    chatWindow.style.display = 'none';
    toggleBtn.innerHTML = '<span class="chat-icon">💬</span>';
  }
}

function handleChatKeyPress(event) {
  if (event.key === 'Enter') {
    sendChatMessage();
  }
}

// Fungsi helper supaya link yang dihasilkan AI bisa diklik
function formatTextToHtml(text) {
  let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/\n/g, '<br>');
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return html.replace(urlRegex, function(url) {
    return '<a href="' + url + '" target="_blank" style="color: #60a5fa; text-decoration: underline;">' + url + '</a>';
  });
}

function appendMessage(sender, text) {
  const chatMessages = document.getElementById('chatMessages');
  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-msg ${sender}`;
  
  if (sender === 'typing') {
    msgDiv.id = 'typingIndicator';
    msgDiv.innerHTML = `
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>`;
  } else {
    msgDiv.innerHTML = `<div class="msg-bubble">${formatTextToHtml(text)}</div>`;
  }
  
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight; 
}

function removeTypingIndicator() {
  const indicator = document.getElementById('typingIndicator');
  if (indicator) indicator.remove();
}

function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  
  if (!message) return;
  
  appendMessage('user', message);
  input.value = ''; 
  
  appendMessage('typing', '');

  const userEmail = (globalUserData && globalUserData.email) ? globalUserData.email : 'guest@trendora.io';
  
  // Nembak ke endpoint backend Flask kita sendiri!
  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      pesan_user: message, 
      email_user: userEmail
    })
  })
  .then(res => res.json())
  .then(data => {
    removeTypingIndicator();
    const botReply = data.balasan || "Maaf, sistem tidak merespon.";
    appendMessage('bot', botReply);
  })
  .catch(err => {
    removeTypingIndicator();
    appendMessage('bot', "Waduh, maaf sepertinya koneksi ke server AI kami sedang terputus 😔 Coba lagi nanti ya.");
    console.error("Chat Error:", err);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  if (typeof checkStoredSession === 'function') checkStoredSession();
  
  if (window.location.pathname === '/checkout') {
    const storedPlan = localStorage.getItem('selectedPlanName') || 'Creator Monthly';
    const storedPrice = localStorage.getItem('selectedPlanPrice') || 'Rp.200.000/mo';
    
    selectedPlanName = storedPlan;
    selectedPlanPrice = storedPrice;
    
    const summaryName = document.getElementById('summaryPlanName');
    const summaryPrice = document.getElementById('summaryPlanPrice');
    if (summaryName) summaryName.innerText = storedPlan;
    if (summaryPrice) summaryPrice.innerText = storedPrice;
  }
  
  if (typeof initCardDetection === 'function') initCardDetection();
});

window.openLegalModal = openLegalModal;
window.closeLegalModal = closeLegalModal;
window.showDashboardPage = showDashboardPage;
window.showLandingPage = showLandingPage;
window.scrollToPricing = scrollToPricing;
window.scrollToDocs = scrollToDocs;
window.openLoginModal = openLoginModal;
window.openRegisterModal = openRegisterModal;
window.handleStartFree = handleStartFree;
window.closeApiModal = closeApiModal;
window.showToast = showToast;
window.renderLoggedInUI = renderLoggedInUI;
window.toggleFaq = toggleFaq;
window.toggleChat = toggleChat;
window.handleChatKeyPress = handleChatKeyPress;
window.sendChatMessage = sendChatMessage;