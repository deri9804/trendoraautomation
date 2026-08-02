function handleSurveySelect(sourceName) {
  if (globalUserData) {
    globalUserData.referralSource = sourceName;
    localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
  }

  showToast("Terima kasih! Feedback Anda tersimpan.", "#34d399");

  const stepSurvey = document.getElementById('modalStepSurvey');
  const stepOnboarding = document.getElementById('modalStepOnboarding');
  
  if (stepSurvey) stepSurvey.style.display = 'none';
  if (stepOnboarding) stepOnboarding.style.display = 'block';
}

function handleUnlockApiClick() {
  showToast("Free Trial Anda Berakhir. Memproses pembuatan API Key...", "#f59e0b");
  
  if (!globalUserData || !globalUserData.email) {
    globalUserData = { name: "User Trial", email: "trial@user.com" };
  }

  const btn = document.querySelector('.btn-unlock-api');
  if (btn) {
    btn.disabled = true;
    btn.innerText = "Memproses Key...";
  }

  setTimeout(() => {
    if (btn) { btn.disabled = false; btn.innerText = "Unlock API access →"; }
    const mockKey = "TREND_" + Math.random().toString(36).substring(2, 12).toUpperCase();
    globalUserData.apiKey = globalUserData.apiKey && globalUserData.apiKey !== '-' ? globalUserData.apiKey : mockKey;
    globalUserData.isPaid = false;
    globalUserData.status = 'Trial Expired (Perlu Langganan)';
    localStorage.setItem('automedia_user', JSON.stringify(globalUserData));

    showLockedResultModal();
  }, 700);
}

function showLockedResultModal() {
  const stepOnboarding = document.getElementById('modalStepOnboarding');
  const stepResult = document.getElementById('modalStepResult');
  if (stepOnboarding) stepOnboarding.style.display = 'none';
  if (stepResult) stepResult.style.display = 'block';

  const keyDisplay = document.getElementById('generatedApiKeyText');
  if (keyDisplay) {
    keyDisplay.innerText = "TREND_•••••••••••••••• (🔒 Terkunci)";
  }

  if (typeof renderLoggedInUI === 'function') renderLoggedInUI(globalUserData, false);
  showToast("Masa Free Trial Berakhir! API Key Anda telah dibuat namun terkunci.", "#ef4444");
}

function handleGenerateApiKeyClick() {
  if (!globalUserData || !globalUserData.email) {
    showToast("Silakan login terlebih dahulu!", "#ef4444");
    return;
  }

  const btn = document.getElementById('btnGenerateApiKey');
  if (btn) {
    btn.disabled = true;
    btn.innerText = "Memproses Key...";
  }

  fetch('/api/generate-api-key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: globalUserData.email })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "🔑 Generate API Key";
    }

    if (data.success) {
      globalUserData.apiKey = data.apiKey;
      localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
      updateDashApiKeyDisplay(data.apiKey);
      showToast(data.message || "🎉 API Key berhasil dibuat!", "#34d399");
    } else {
      if (data.isPaid === false) {
        showToast(data.message || "Akun Anda masih Free Trial! Membuka menu pembayaran...", "#f59e0b");
        setTimeout(() => {
          openUpgradePayment();
        }, 1200);
      } else {
        showToast(data.message || "Gagal membuat API Key", "#ef4444");
      }
    }
  })
  .catch(err => {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "🔑 Generate API Key";
    }
    showToast("Server Error saat membuat API Key: " + err, "#ef4444");
  });
}

function openUpgradePayment() {
  const storedToken = lastSnapToken || localStorage.getItem('automedia_snap_token');
  if (storedToken && window.snap) {
    if (typeof reopenSnapPayment === 'function') reopenSnapPayment();
    return;
  }

  if (typeof openRegisterModal === 'function') openRegisterModal();
  showToast("Selesaikan pembayaran bulanan untuk membuka & menyalin API Key.", "#6366f1");
}

function finishOnboardingToDashboard() {
  if (window.location.pathname === '/checkout') {
    window.location.href = '/dashboard';
  } else {
    if (typeof closeApiModal === 'function') closeApiModal();
    showDashboardPage();
    showToast("Selamat datang di Dashboard!", "#34d399");
  }
}

function updateDashApiKeyDisplay(key) {
  const display = document.getElementById('dashApiKeyDisplay');
  const maskBtn = document.getElementById('btnToggleKeyMask');
  const copyBtn = document.getElementById('btnCopyApiKey');
  if (!display) return;
  
  if (!key || key === '-') {
    display.innerText = 'Belum Ada API Key (Klik Generate API Key)';
    display.style.color = '#9ca3af';
    if (maskBtn) maskBtn.style.display = 'none';
    if (copyBtn) copyBtn.style.display = 'none';
    return;
  }

  if (globalUserData && !globalUserData.isPaid) {
    display.innerText = 'TREND_•••••••••••••••• (🔒 Terkunci)';
    display.style.color = '#f87171';
    if (maskBtn) {
      maskBtn.style.display = 'inline-block';
      maskBtn.innerText = '🔒 Buka Key';
    }
    if (copyBtn) copyBtn.style.display = 'none';
    return;
  }

  display.style.color = '#34d399';
  if (maskBtn) maskBtn.style.display = 'inline-block';
  if (copyBtn) copyBtn.style.display = 'inline-block';

  if (isKeyMasked) {
    display.innerText = key.substring(0, 8) + '••••••••••••••••';
    if (maskBtn) maskBtn.innerText = '👁️ Show';
  } else {
    display.innerText = key;
    if (maskBtn) maskBtn.innerText = '🙈 Hide';
  }
}

function toggleApiKeyMask() {
  if (globalUserData && !globalUserData.isPaid) {
    showToast('🔒 API Key Terkunci! Bayar langganan bulanan untuk melihat API Key.', '#ef4444');
    openUpgradePayment();
    return;
  }

  isKeyMasked = !isKeyMasked;
  if (globalUserData && globalUserData.apiKey) {
    updateDashApiKeyDisplay(globalUserData.apiKey);
  }
}

function copyDashApiKey() {
  if (!globalUserData || !globalUserData.apiKey || globalUserData.apiKey === '-') {
    showToast('Belum ada API Key untuk disalin!', '#ef4444');
    return;
  }

  if (!globalUserData.isPaid) {
    showToast('🔒 API Key Terkunci! Bayar langganan bulanan untuk menyalin API Key.', '#ef4444');
    openUpgradePayment();
    return;
  }

  navigator.clipboard.writeText(globalUserData.apiKey).then(() => {
    showToast('API Key disalin ke clipboard! 📋', '#34d399');
  });
}

function loadWebhookUrl() {
  const display = document.getElementById('dashWebhookUrlDisplay');
  if (!display) return;

  const currentUrl = window.location.origin + '/api/n8n-webhook';
  display.innerText = currentUrl;
  display.setAttribute('data-fullurl', currentUrl);
}

function copyWebhookUrl() {
  const display = document.getElementById('dashWebhookUrlDisplay');
  const fullUrl = display ? display.getAttribute('data-fullurl') || display.innerText : '';

  if (!fullUrl || fullUrl === 'Memuat Webhook URL...') {
    showToast('URL Webhook belum siap disalin!', '#ef4444');
    return;
  }

  navigator.clipboard.writeText(fullUrl).then(() => {
    showToast('URL Webhook Endpoint disalin ke clipboard! 📋', '#34d399');
  });
}

function loadUserPostLogs() {
  const tbody = document.getElementById('dashLogsTableBody');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #9ca3af;">⏳ Memuat log postingan real-time dari database...</td></tr>';

  const apiKey = globalUserData ? globalUserData.apiKey : '';

  fetch('/api/get-logs', {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'X-API-Key': apiKey 
    },
    body: JSON.stringify({})
  })
  .then(res => res.json())
  .then(res => {
    if (res.success) {
      renderLogsTable(res);
    } else {
      tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #ef4444;">✕ Gagal memuat log: ' + res.message + '</td></tr>';
    }
  })
  .catch(err => {
    tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #ef4444;">✕ Server error saat memuat log: ' + err + '</td></tr>';
  });
}

function renderLogsTable(res) {
  const tbody = document.getElementById('dashLogsTableBody');
  if (!tbody) return;

  if (!res.logs || res.logs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #6b7280;">Belum ada log aktivitas. Pastikan Anda mengirim POST ke webhook web ini dari n8n!</td></tr>';
    return;
  }

  let html = '';
  res.logs.forEach(log => {
    const logStatus = (log.Status || 'UNKNOWN').toUpperCase();
    const isSuccess = logStatus.includes('PUBLISH') || logStatus.includes('SUCCESS') || logStatus.includes('DRAFT');
    const statusBadge = isSuccess ? 'background: rgba(16, 185, 129, 0.15); color: #34d399;' : 'background: rgba(239, 68, 68, 0.15); color: #f87171;';
    
    let detailsStr = log.Details;
    try {
        const parsed = JSON.parse(log.Details);
        detailsStr = parsed.caption || parsed.tiktok_api_trace || parsed.media_url || JSON.stringify(parsed);
    } catch(e) {}

    html += '<tr style="border-bottom: 1px solid rgba(255,255,255,0.05); color: #e5e7eb;">';
    html += '<td style="padding: 12px; font-size: 12px; white-space: nowrap;">' + (log.Timestamp || '-') + '</td>';
    html += '<td style="padding: 12px; font-family: monospace; font-size: 12px; color: #818cf8;">' + (log.LogID || '-') + '</td>';
    html += '<td style="padding: 12px; text-transform: capitalize; font-weight: 600;">' + (log.Platform || '-') + '</td>';
    html += '<td style="padding: 12px;"><span style="font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 10px; ' + statusBadge + '">' + logStatus + '</span></td>';
    html += '<td style="padding: 12px; font-size: 12px; color: #9ca3af; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title=\'' + detailsStr + '\'>' + detailsStr + '</td>';
    html += '</tr>';
  });

  tbody.innerHTML = html;
}

const SUPPORTED_PLATFORMS = [
  { id: 'TikTok', icon: '🎵', name: 'TikTok', bg: '#000000' },
  { id: 'Instagram', icon: '📷', name: 'Instagram', bg: '#d62976' },
  { id: 'YouTube', icon: '▶️', name: 'YouTube', bg: '#ff0000' },
  { id: 'Facebook', icon: 'f', name: 'Facebook', bg: '#1877f2' },
  { id: 'Twitter', icon: '𝕏', name: 'X / Twitter', bg: '#000000' },
  { id: 'LinkedIn', icon: 'in', name: 'LinkedIn', bg: '#2867b2' },
  { id: 'Threads', icon: '@', name: 'Threads', bg: '#000000' },
];

function renderSocialConnectionsUI() {
  const container = document.getElementById('socialConnectionsList');
  if (!container) return;

  const connected = (globalUserData && globalUserData.connectedPlatforms) ? globalUserData.connectedPlatforms : [];
  let html = '';

  SUPPORTED_PLATFORMS.forEach(plat => {
    const isConnected = connected.includes(plat.id);
    
    if (isConnected) {
      // Tombol menjadi fitur 'Disconnect' ketika disentuh
      html += `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(52, 211, 153, 0.4); border-radius: 12px; padding: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 32px; height: 32px; border-radius: 8px; background: ${plat.bg}; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 800;">
              ${plat.icon}
            </div>
            <span style="font-size: 14px; font-weight: 600; color: #fff;">${plat.name}</span>
          </div>
          <button onclick="handleDisconnectSocial('${plat.id}')" style="background: rgba(52, 211, 153, 0.15); border: 1px solid #34d399; color: #34d399; padding: 8px 14px; border-radius: 8px; font-size: 11px; font-weight: 700; cursor: pointer; transition: all 0.2s ease;" onmouseover="this.innerText='Putuskan ✖'; this.style.borderColor='#ef4444'; this.style.color='#ef4444'; this.style.background='rgba(239, 68, 68, 0.15)';" onmouseout="this.innerText='Connected ✓'; this.style.borderColor='#34d399'; this.style.color='#34d399'; this.style.background='rgba(52, 211, 153, 0.15)';">
            Connected ✓
          </button>
        </div>
      `;
    } else {
      html += `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 32px; height: 32px; border-radius: 8px; background: #1e293b; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 800; border: 1px solid rgba(255,255,255,0.1);">
              ${plat.icon}
            </div>
            <span style="font-size: 14px; font-weight: 600; color: #cbd5e1;">${plat.name}</span>
          </div>
          <button onclick="handleSocialPlatformConnect('${plat.id}')" style="background: #1e293b; border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 8px 14px; border-radius: 8px; font-size: 11px; font-weight: 700; cursor: pointer; transition: all 0.2s ease;" onmouseover="this.style.background='#334155'" onmouseout="this.style.background='#1e293b'">
            Hubungkan 🔗
          </button>
        </div>
      `;
    }
  });

  container.innerHTML = html;
}

window.handleSurveySelect = handleSurveySelect;
window.handleUnlockApiClick = handleUnlockApiClick;
window.handleGenerateApiKeyClick = handleGenerateApiKeyClick;
window.openUpgradePayment = openUpgradePayment;
window.finishOnboardingToDashboard = finishOnboardingToDashboard;
window.updateDashApiKeyDisplay = updateDashApiKeyDisplay;
window.toggleApiKeyMask = toggleApiKeyMask;
window.copyDashApiKey = copyDashApiKey;
window.loadWebhookUrl = loadWebhookUrl;
window.copyWebhookUrl = copyWebhookUrl;
window.loadUserPostLogs = loadUserPostLogs;
window.renderLogsTable = renderLogsTable;
window.renderSocialConnectionsUI = renderSocialConnectionsUI;