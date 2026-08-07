function handleLogout() {
  if (typeof stopPaymentStatusPolling === 'function') stopPaymentStatusPolling();
  localStorage.removeItem('automedia_user');
  localStorage.removeItem('automedia_snap_token');
  globalUserData = null;
  lastSnapToken = null;

  const navGuest = document.getElementById('navGuestGroup');
  const navUser = document.getElementById('navUserGroup');
  const navDashLink = document.getElementById('navDashLink');

  if (navGuest) navGuest.style.display = 'flex';
  if (navUser) navUser.style.display = 'none';
  if (navDashLink) navDashLink.style.display = 'none';

  if (window.location.pathname !== '/') {
    window.location.href = '/';
  } else {
    showLandingPage();
    showToast('Berhasil keluar dari akun.', '#34d399');
  }
}

function checkStoredSession() {
  try {
    const savedUser = localStorage.getItem('automedia_user');
    if (savedUser) {
      globalUserData = JSON.parse(savedUser);
      renderLoggedInUI(globalUserData, false);
      
      // Silent sync dengan database tiap kali halamannya dimuat
      if (globalUserData && globalUserData.email) {
        fetch('/api/me', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: globalUserData.email })
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            globalUserData = data.user;
            localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
            renderLoggedInUI(globalUserData, false);
          }
        })
        .catch(err => console.log("Sync error:", err));
      }
    }
  } catch (e) {
    console.error('Session parse error:', e);
  }
}


window.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'OAUTH_SUCCESS') {
    const platform = event.data.platform || 'Social Account';
    showToast(`🎉 Akun asli ${platform} berhasil terhubung & token diamankan!`, "#34d399");

    if (typeof closeSocialConnectModal === 'function') {
        closeSocialConnectModal();
    }

    if (globalUserData) {
      if (!globalUserData.connectedPlatforms) {
        globalUserData.connectedPlatforms = [];
      }
      
      // Jika yang login adalah Meta, aktifkan badge FB dan IG sekaligus
      if (platform === 'Meta') {
          if (!globalUserData.connectedPlatforms.includes('Facebook')) globalUserData.connectedPlatforms.push('Facebook');
          if (!globalUserData.connectedPlatforms.includes('Instagram')) globalUserData.connectedPlatforms.push('Instagram');
      } else {
          if (!globalUserData.connectedPlatforms.includes(platform)) {
            globalUserData.connectedPlatforms.push(platform);
          }
      }
      
      localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
      
      if (typeof renderSocialConnectionsUI === 'function') {
        renderSocialConnectionsUI();
      }
    }
  }
});


function handleConnectSocialClick() {
  const socialOverlay = document.getElementById('socialConnectOverlay');
  if (socialOverlay) {
    socialOverlay.style.display = 'flex';
  }
}

function closeSocialConnectModal() {
  const socialOverlay = document.getElementById('socialConnectOverlay');
  if (socialOverlay) {
    socialOverlay.style.display = 'none';
  }
}

function handleSocialPlatformConnect(platform) {
  const userEmail = (globalUserData && globalUserData.email) ? globalUserData.email : 'guest@trendora.io';
  showToast(`Membuka jendela login otentikasi resmi ${platform}...`, "#6366f1");

  const p = String(platform).toLowerCase();

  // 100% REAL TIKTOK AUTHENTICATION (Menitipkan email agar backend tau Token milik siapa)
  if (p === 'tiktok') {
    fetch('/api/tiktok-auth-url?email=' + encodeURIComponent(userEmail))
      .then(res => res.json())
      .then(data => {
        if (data.success && data.url) {
          window.open(data.url, `OAuth_${platform}`, 'width=600,height=750,scrollbars=yes,status=yes');
        } else {
          openFallbackOAuthPopup(platform, userEmail);
        }
      })
      .catch(err => {
        openFallbackOAuthPopup(platform, userEmail);
      });
    return;
  }

  // REAL META AUTHENTICATION (FB & IG)
  if (p === 'facebook' || p === 'instagram') {
    fetch('/api/meta-auth-url?email=' + encodeURIComponent(userEmail))
      .then(res => res.json())
      .then(data => {
        if (data.success && data.url) {
          window.open(data.url, `OAuth_Meta`, 'width=600,height=750,scrollbars=yes,status=yes');
        } else {
          openFallbackOAuthPopup(platform, userEmail);
        }
      })
      .catch(err => {
        openFallbackOAuthPopup(platform, userEmail);
      });
    return;
  }

  // REAL LINKEDIN AUTHENTICATION
  if (p === 'linkedin') {
    fetch('/api/linkedin-auth-url?email=' + encodeURIComponent(userEmail))
      .then(res => res.json())
      .then(data => {
        if (data.success && data.url) {
          window.open(data.url, `OAuth_LinkedIn`, 'width=600,height=750,scrollbars=yes,status=yes');
        } else {
          openFallbackOAuthPopup(platform, userEmail);
        }
      })
      .catch(err => {
        openFallbackOAuthPopup(platform, userEmail);
      });
    return;
  }

  // REAL YOUTUBE (GOOGLE) AUTHENTICATION
  if (p === 'youtube' || p === 'google') {
    fetch('/api/youtube-auth-url?email=' + encodeURIComponent(userEmail))
      .then(res => res.json())
      .then(data => {
        if (data.success && data.url) {
          window.open(data.url, `OAuth_YouTube`, 'width=600,height=750,scrollbars=yes,status=yes');
        } else {
          openFallbackOAuthPopup(platform, userEmail);
        }
      })
      .catch(err => {
        openFallbackOAuthPopup(platform, userEmail);
      });
    return;
  }

  // REAL THREADS AUTHENTICATION
  if (p === 'threads') {
    fetch('/api/threads-auth-url?email=' + encodeURIComponent(userEmail))
      .then(res => res.json())
      .then(data => {
        if (data.success && data.url) {
          window.open(data.url, `OAuth_Threads`, 'width=600,height=750,scrollbars=yes,status=yes');
        } else {
          openFallbackOAuthPopup(platform, userEmail);
        }
      })
      .catch(err => {
        openFallbackOAuthPopup(platform, userEmail);
      });
    return;
  }

  // REAL TWITTER AUTHENTICATION
  if (p === 'twitter' || p === 'x') {
    fetch('/api/twitter-auth-url?email=' + encodeURIComponent(userEmail))
      .then(res => res.json())
      .then(data => {
        if (data.success && data.url) {
          window.open(data.url, `OAuth_Twitter`, 'width=600,height=750,scrollbars=yes,status=yes');
        } else {
          openFallbackOAuthPopup(platform, userEmail);
        }
      })
      .catch(err => {
        openFallbackOAuthPopup(platform, userEmail);
      });
    return;
  }

  // PLATFORM LAIN (Pinterest, dll - Pakai Fallback)
  openFallbackOAuthPopup(platform, userEmail);
}

function openFallbackOAuthPopup(platform, userEmail) {
  let authUrl = '';
  const p = String(platform).toLowerCase();

  if (p === 'youtube' || p === 'google') {
    authUrl = 'https://accounts.google.com/o/oauth2/v2/auth';
  } else if (p === 'facebook' || p === 'instagram') {
    authUrl = 'https://www.facebook.com/v18.0/dialog/oauth';
  } else if (p === 'twitter' || p === 'x') {
    authUrl = 'https://twitter.com/i/oauth2/authorize';
  } else if (p === 'linkedin') {
    authUrl = 'https://www.linkedin.com/oauth/v2/authorization';
  } else {
    authUrl = 'https://accounts.google.com/o/oauth2/v2/auth';
  }

  // MURNI MEMBUKA JENDELA ASLI TANPA DUMMY TIMER APAPUN
  window.open(authUrl, `OAuth_${platform}`, 'width=600,height=750,scrollbars=yes,status=yes');
}


function handleDisconnectSocial(platform) {
  if (globalUserData && globalUserData.email) {
    // Tampilkan toast bahwa sedang memproses pemutusan
    showToast(`Memutuskan koneksi dari ${platform}...`, "#f59e0b");

    // Hit endpoint backend baru untuk MENGHAPUS token secara nyata di Database
    fetch('/api/disconnect-social', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: globalUserData.email, platform: platform })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        if (globalUserData.connectedPlatforms) {
          // Jika memutus Meta, pastikan FB & IG terputus karena menggunakan Token yang sama
          if (platform === 'Facebook' || platform === 'Instagram') {
              globalUserData.connectedPlatforms = globalUserData.connectedPlatforms.filter(p => p !== 'Facebook' && p !== 'Instagram');
          } else {
              globalUserData.connectedPlatforms = globalUserData.connectedPlatforms.filter(p => p !== platform);
          }
          localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
        }
        
        if (typeof renderSocialConnectionsUI === 'function') {
          renderSocialConnectionsUI();
        }
        
        showToast(`Koneksi ke ${platform} berhasil diputuskan secara permanen.`, "#34d399");
      } else {
        showToast("Gagal memutuskan koneksi: " + (data.message || ""), "#ef4444");
      }
    })
    .catch(err => {
      showToast("Server error saat mencoba memutuskan koneksi.", "#ef4444");
    });
  }
}


function handleRequestOTP(event) {
  event.preventDefault();
  const emailInput = document.getElementById('loginEmail');
  const email = emailInput ? emailInput.value.trim() : '';
  const btn = document.getElementById('btnRequestOTP');
  const alertMsg = document.getElementById('loginAlertMsg');
  const qrContainer = document.getElementById('qrCodeContainer');
  const otpGroup = document.getElementById('otpInputGroup');

  if (!email) {
    if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = "Masukkan email terlebih dahulu!"; }
    return;
  }

  if (btn) { btn.disabled = true; btn.innerText = "Mengirim..."; }
  if (alertMsg) alertMsg.innerText = "";

  fetch('/api/request-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) { btn.disabled = false; btn.innerText = "Kirim Ulang OTP"; }
    
    if (data.success) {
      if (otpGroup) otpGroup.style.display = 'block';
      
      const qrImage = document.getElementById('qrCodeImage');
      
      if (!data.is2faLinked && data.qrCodeUrl) {
        if (qrImage) qrImage.src = data.qrCodeUrl;
        if (qrContainer) qrContainer.style.display = 'block';
      } else {
        if (qrContainer) qrContainer.style.display = 'none';
      }

      showToast(data.message || "Silakan cek Google Authenticator Anda", "#34d399");
    } else {
      if (qrContainer) qrContainer.style.display = 'none';
      if (otpGroup) otpGroup.style.display = 'none';
      if (alertMsg) { 
        alertMsg.style.color = '#ef4444'; 
        alertMsg.innerText = data.message || "Email belum terdaftar! Silakan mendaftar akun terlebih dahulu."; 
      }
      showToast(data.message || "Email tidak terdaftar!", "#ef4444");
    }
  })
  .catch(err => {
    if (btn) { btn.disabled = false; btn.innerText = "Kirim Ulang OTP"; }
    if (qrContainer) qrContainer.style.display = 'none';
    if (otpGroup) otpGroup.style.display = 'none';
    if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = "Gagal terhubung ke server. Periksa koneksi internet Anda."; }
    showToast("Terjadi kesalahan koneksi ke server", "#ef4444");
  });
}

function handleVerifyOTP(event) {
  event.preventDefault();
  const emailInput = document.getElementById('loginEmail');
  const otpInput = document.getElementById('loginOTP');
  const email = emailInput ? emailInput.value.trim() : '';
  const otp = otpInput ? otpInput.value.trim() : '';
  const btn = document.getElementById('btnVerifyOTP');
  const alertMsg = document.getElementById('loginAlertMsg');

  if (!otp) {
    if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = "Masukkan kode OTP!"; }
    return;
  }

  if (btn) { btn.disabled = true; btn.innerText = "Memverifikasi..."; }
  
  fetch('/api/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email, otp: otp })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) { btn.disabled = false; btn.innerText = "Verifikasi & Masuk ✓"; }
    if (data.success) {
      const qrContainer = document.getElementById('qrCodeContainer');
      if (qrContainer) qrContainer.style.display = 'none';
      
      const otpGroup = document.getElementById('otpInputGroup');
      if (otpGroup) {
        otpGroup.style.display = 'none';
        document.getElementById('loginOTP').value = ""; 
      }

      onLoginSuccess({ success: true, user: data.user });
    } else {
      if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = data.message || "OTP Salah"; }
    }
  })
  .catch(err => {
    if (btn) { btn.disabled = false; btn.innerText = "Verifikasi & Masuk ✓"; }
    if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = "Terjadi kesalahan koneksi saat memverifikasi OTP."; }
  });
}

function handleReset2FA() {
  const emailInput = document.getElementById('loginEmail');
  const email = emailInput ? emailInput.value.trim() : '';
  if (!email) {
    showToast("Masukkan email Anda terlebih dahulu lalu klik Kirim OTP!", "#ef4444");
    return;
  }
  
  showToast("Memproses reset & mengirim email...", "#f59e0b");
  
  fetch('/api/reset-2fa-qr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      showToast(data.message, "#34d399");
      
      const qrContainer = document.getElementById('qrCodeContainer');
      if (qrContainer) qrContainer.style.display = 'none';
      
      const btnOtp = document.getElementById('btnRequestOTP');
      if (btnOtp) btnOtp.click();
    } else {
      showToast(data.message || "Gagal mereset 2FA", "#ef4444");
    }
  })
  .catch(err => {
    showToast("Server error saat mereset 2FA", "#ef4444");
  });
}

function onLoginSuccess(res) {
  const alertMsg = document.getElementById('loginAlertMsg');

  if (!res.success) {
    if (alertMsg) {
      alertMsg.style.color = '#ef4444';
      alertMsg.innerText = res.message || "Gagal login";
    }
    return;
  }

  globalUserData = res.user;
  localStorage.setItem('automedia_user', JSON.stringify(res.user));

  if (window.location.pathname === '/login') {
    window.location.href = '/dashboard';
  } else {
    if (typeof closeApiModal === 'function') closeApiModal();
    renderLoggedInUI(res.user, true);
    showToast("Selamat datang kembali, " + res.user.name + "!", "#34d399");
  }
}

window.handleLogout = handleLogout;
window.checkStoredSession = checkStoredSession;
window.handleConnectSocialClick = handleConnectSocialClick;
window.closeSocialConnectModal = closeSocialConnectModal;
window.handleSocialPlatformConnect = handleSocialPlatformConnect;
window.handleDisconnectSocial = handleDisconnectSocial;
window.handleRequestOTP = handleRequestOTP;
window.handleVerifyOTP = handleVerifyOTP;
window.handleReset2FA = handleReset2FA;
window.onLoginSuccess = onLoginSuccess;