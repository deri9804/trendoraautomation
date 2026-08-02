var globalUserData = null;
var isKeyMasked = true;
var currentViewMode = 'landing';
var selectedPlanName = 'Creator Monthly';
var selectedPlanPrice = 'Rp.200.000/mo';
var lastSnapToken = localStorage.getItem('automedia_snap_token') || null;
var paymentPollingInterval = null;

const LEGAL_DOCUMENTS = {
  tos: `<h4>1. Deskripsi Layanan</h4><p>TRENDORA menyediakan antarmuka API dan community node...</p>`,
  privacy: `<h4>1. Informasi yang Kami Kumpulkan</h4><ul><li><strong>Informasi Akun:</strong> Nama lengkap, email...</li></ul>`
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