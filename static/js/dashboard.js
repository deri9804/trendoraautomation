let isSandboxMode = false;

function toggleSandboxMode() {
  isSandboxMode = !isSandboxMode;
  const btn = document.getElementById('btnSandboxToggle');
  const icon = document.getElementById('sandboxIcon');
  const panel = document.getElementById('tiktokSandboxPanel');

  if (isSandboxMode) {
    if (btn) {
      btn.style.background = 'rgba(56, 189, 248, 0.15)';
      btn.style.color = '#38bdf8';
      btn.style.borderColor = '#38bdf8';
    }
    if (icon) icon.innerText = '📲';
    if (panel) panel.style.display = 'block';
    showToast('Mode Sandbox Aktif! Panel simulasi TikTok terbuka.', '#38bdf8');
  } else {
    if (btn) {
      btn.style.background = 'transparent';
      btn.style.color = '#9ca3af';
      btn.style.borderColor = 'rgba(255,255,255,0.15)';
    }
    if (icon) icon.innerText = '📴';
    if (panel) panel.style.display = 'none';
    showToast('Mode Sandbox Dimatikan. Kembali ke Mode Live (Production).', '#34d399');
  }
}

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
  if (!display) return;
  
  if (!key || key === '-') {
    display.innerText = 'Belum Ada API Key (View-Only Trial)';
    if (maskBtn) maskBtn.style.display = 'none';
    return;
  }

  if (globalUserData && !globalUserData.isPaid) {
    display.innerText = 'TREND_•••••••••••••••• (🔒 Terkunci)';
    display.style.color = '#f87171';
    if (maskBtn) {
      maskBtn.style.display = 'inline-block';
      maskBtn.innerText = '🔒 Buka Key';
    }
    return;
  }

  display.style.color = '#34d399';
  if (maskBtn) maskBtn.style.display = 'inline-block';

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

function runTikTokSandbox(mode) {
  const consoleBox = document.getElementById('tiktokSandboxConsole');
  if (consoleBox) {
    consoleBox.style.display = 'block';
    consoleBox.innerHTML = `<p class="cmd">> Inisiasi simulasi TikTok API (${mode.toUpperCase()})...</p>`;
  }

  const apiKey = globalUserData ? globalUserData.apiKey : 'TREND_TESTER';

  fetch('/api/n8n-webhook', {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'X-API-Key': apiKey 
    },
    body: JSON.stringify({
      platform: "tiktok",
      post_mode: mode,
      is_sandbox: true, // FLAG UNTUK MEMASTIKAN BACKEND MENGGUNAKAN SIMULASI
      status: mode === 'draft' ? "DRAFT_UPLOADED" : "PUBLISHED",
      details: { caption: `[Auto Test] TikTok Sandbox - ${mode.toUpperCase()}`, media_url: "https://domain.com/sample_video.mp4" }
    })
  })
  .then(res => res.json())
  .then(data => {
    if (consoleBox) {
      if (data.success) {
        consoleBox.innerHTML += `<p class="success">✓ Payload berhasil diproses (API Otorisasi: ${mode === 'draft' ? 'video.upload' : 'video.publish'})</p>`;
        if (data.tiktok_sandbox_trace) {
           consoleBox.innerHTML += `<p class="param">Response dari Endpoint TikTok:</p>`;
           consoleBox.innerHTML += `<pre style="color: #60a5fa; margin-top: 8px;">${JSON.stringify(data.tiktok_sandbox_trace, null, 2)}</pre>`;
        }
      } else {
        consoleBox.innerHTML += `<p style="color: #ef4444;">✕ Error: ${data.message}</p>`;
      }
    }
    if (data.success) {
      setTimeout(loadUserPostLogs, 1500); 
    }
  })
  .catch(err => {
    if (consoleBox) consoleBox.innerHTML += `<p style="color: #ef4444;">✕ Server Error: ${err}</p>`;
  });
}

function runWebhookTest(context) {
  const isDoc = context === 'doc';
  const inputId = isDoc ? 'videoUrlInputDoc' : 'videoUrlInputHero';
  const btnId = isDoc ? 'btnTestWebhookDoc' : 'btnTestWebhookHero';
  const consoleId = isDoc ? 'terminalConsoleDoc' : 'terminalConsoleHero';

  const inputEl = document.getElementById(inputId);
  const videoUrl = inputEl ? inputEl.value : '';
  const btn = document.getElementById(btnId);
  const consoleBox = document.getElementById(consoleId);

  if (!videoUrl) {
    showToast('Masukkan URL Video terlebih dahulu!', '#ef4444');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerText = "Processing...";
  }
  if (consoleBox) {
    consoleBox.innerHTML = '<p class="cmd">> POST /api/n8n-webhook</p><p class="param">> Connecting to Backend Webhook Listener...</p>';
  }

  const apiKey = globalUserData ? globalUserData.apiKey : 'TREND_TESTER';

  fetch('/api/n8n-webhook', {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'X-API-Key': apiKey 
    },
    body: JSON.stringify({
      platform: "instagram",
      status: "PUBLISHED",
      is_sandbox: isSandboxMode, // KIRIM STATUS SANDBOX KE BACKEND
      details: { caption: "Webhook Auto-Test from Web UI", media_url: videoUrl }
    })
  })
  .then(res => res.json())
  .then(data => {
    renderSimulationResult(data, btn, consoleBox);
    if (data.success) {
      setTimeout(loadUserPostLogs, 1500); 
    }
  })
  .catch(err => {
    handleSimulationError(err, btn, consoleBox);
  });
}

function renderSimulationResult(res, btn, consoleBox) {
  if (btn) {
    btn.disabled = false;
    btn.innerText = "Test Webhook ⚡";
  }

  if (!res.success) {
    if (consoleBox) consoleBox.innerHTML += '<p style="color: #ef4444;">✕ Error: ' + res.message + '</p>';
    return;
  }

  let html = '';
  html += '<p><span class="cmd">> POST /api/n8n-webhook</span></p>';
  html += '<p class="success">✓ Payload successfully processed by Web Backend</p>';
  
  if (res.sandbox_active) {
     html += '<p style="color: #38bdf8;">⚠️ (Processed in Sandbox Simulation Mode)</p>';
  }
  
  html += '<p><span class="param">Response JSON:</span></p>';
  html += '<pre style="color: #34d399; font-size: 11px;">' + JSON.stringify(res, null, 2) + '</pre>';

  if (consoleBox) consoleBox.innerHTML = html;
}

function handleSimulationError(err, btn, consoleBox) {
  if (btn) {
    btn.disabled = false;
    btn.innerText = "Test Webhook ⚡";
  }
  if (consoleBox) consoleBox.innerHTML += '<p style="color: #ef4444;">✕ Server Error: ' + err + '</p>';
}

document.addEventListener('DOMContentLoaded', () => {
   // Cek apakah ada data profile mock TikTok
   setTimeout(() => {
     if (globalUserData && globalUserData.tiktokAvatar) {
         const dashAvatar = document.getElementById('dashAvatar');
         // REVISI: Logika penimpaan dashName sengaja DIHAPUS agar nama asli user tetap tampil
         
         if (dashAvatar) {
            dashAvatar.src = globalUserData.tiktokAvatar;
            dashAvatar.style.display = 'block';
         }
     }
   }, 500);
});

window.toggleSandboxMode = toggleSandboxMode;
window.handleSurveySelect = handleSurveySelect;
window.handleUnlockApiClick = handleUnlockApiClick;
window.openUpgradePayment = openUpgradePayment;
window.finishOnboardingToDashboard = finishOnboardingToDashboard;
window.updateDashApiKeyDisplay = updateDashApiKeyDisplay;
window.toggleApiKeyMask = toggleApiKeyMask;
window.copyDashApiKey = copyDashApiKey;
window.loadWebhookUrl = loadWebhookUrl;
window.copyWebhookUrl = copyWebhookUrl;
window.loadUserPostLogs = loadUserPostLogs;
window.runWebhookTest = runWebhookTest;
window.runTikTokSandbox = runTikTokSandbox;