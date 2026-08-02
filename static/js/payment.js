function startPaymentStatusPolling() {
  if (paymentPollingInterval) return;

  paymentPollingInterval = setInterval(() => {
    if (!globalUserData || !globalUserData.email || globalUserData.isPaid) {
      stopPaymentStatusPolling();
      return;
    }

    fetch('/api/check-payment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: globalUserData.email })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success && data.isPaid) {
        stopPaymentStatusPolling();
        
        globalUserData.isPaid = true;
        globalUserData.status = data.status || 'Active Subscriber (Paid)';
        globalUserData.apiKey = data.apiKey || globalUserData.apiKey;
        
        localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
        localStorage.removeItem('automedia_snap_token');
        lastSnapToken = null;

        if (typeof renderLoggedInUI === 'function') renderLoggedInUI(globalUserData, false);
        showToast("🎉 Pembayaran Berhasil Dikonfirmasi! Akun & API Key Terbuka!", "#34d399");
      }
    })
    .catch(err => console.error("Polling error:", err));
  }, 6000);
}

function stopPaymentStatusPolling() {
  if (paymentPollingInterval) {
    clearInterval(paymentPollingInterval);
    paymentPollingInterval = null;
  }
}

function selectPayMethod(btn, method) {
  document.querySelectorAll('.pay-method-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  
  const cardGroup = document.getElementById('cardDetailsGroup');
  const ewalletGroup = document.getElementById('ewalletDetailsGroup');
  const bankGroup = document.getElementById('bankDetailsGroup');

  if (cardGroup) cardGroup.style.display = 'none';
  if (ewalletGroup) ewalletGroup.style.display = 'none';
  if (bankGroup) bankGroup.style.display = 'none';

  if (method === 'card' && cardGroup) {
    cardGroup.style.display = 'block';
  } else if (method === 'ewallet' && ewalletGroup) {
    ewalletGroup.style.display = 'block';
  } else if (method === 'bank' && bankGroup) {
    bankGroup.style.display = 'block';
  }
}

function initCardDetection() {
  const cardInput = document.getElementById('regCardNumber');
  if (!cardInput) return;

  cardInput.addEventListener('input', function(e) {
    let val = this.value.replace(/\D/g, ''); 
    
    let formatted = val.match(/.{1,4}/g)?.join(' ') || '';
    this.value = formatted;

    const visa = document.querySelector('.brand-badge.visa');
    const mc = document.querySelector('.brand-badge.mc');
    const jcb = document.querySelector('.brand-badge.jcb');
    
    if(visa) visa.style.opacity = '0.3';
    if(mc) mc.style.opacity = '0.3';
    if(jcb) jcb.style.opacity = '0.3';

    if (val.length === 0) {
        if(visa) visa.style.opacity = '1';
        if(mc) mc.style.opacity = '1';
        if(jcb) jcb.style.opacity = '1';
        return;
    }

    if (val.startsWith('4')) {
      if(visa) visa.style.opacity = '1';
    } else if (/^5[1-5]/.test(val) || /^2(2[2-9][1-9]|[3-6]\d\d|7[0-1]\d|720)/.test(val)) {
      if(mc) mc.style.opacity = '1';
    } else if (/^35/.test(val)) {
      if(jcb) jcb.style.opacity = '1';
    }
  });
}

/* REVISI: Fungsi KHUSUS untuk "Start my free trial" (Daftar Akun Gratis tanpa API Midtrans) */
function handleFreeTrial(event) {
  event.preventDefault();
  const btn = document.getElementById('btnFreeTrial');
  const alertMsg = document.getElementById('checkoutAlertMsg');

  const firstName = document.getElementById('regFirstName')?.value || '';
  const lastName = document.getElementById('regLastName')?.value || '';
  const fullName = (firstName + ' ' + lastName).trim();
  const email = document.getElementById('regEmail')?.value || '';

  if (!email || !firstName) {
    if(alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = "Harap isi Nama dan Email Anda!"; }
    return;
  }

  if (btn) { btn.disabled = true; btn.innerText = "Mendaftarkan..."; }
  if (alertMsg) alertMsg.innerText = "";

  fetch('/api/register-trial', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: fullName, email: email })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) { btn.disabled = false; btn.innerText = "Start my free trial"; }
    
    if (data.success) {
      globalUserData = data.user;
      localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
      
      document.getElementById('modalStepForm').style.display = 'none';
      document.getElementById('modalStepSurvey').style.display = 'block';
      
      if (typeof renderLoggedInUI === 'function') renderLoggedInUI(globalUserData, false);
      showToast(data.message, "#34d399");
    } else {
      if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = data.message; }
      showToast(data.message, "#ef4444");
    }
  })
  .catch(err => {
    if (btn) { btn.disabled = false; btn.innerText = "Start my free trial"; }
    if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = "Server Timeout: Koneksi gagal."; }
  });
}

/* REVISI: Fungsi KHUSUS untuk tombol "Bayar Sekarang" (Midtrans API) dengan deteksi akun ganda */
function handleCheckoutSubmit(event) {
  event.preventDefault();
  const btn = document.getElementById('btnRegisterSubmit');
  const alertMsg = document.getElementById('checkoutAlertMsg');

  if (btn) { btn.disabled = true; btn.innerText = "Menghubungkan ke Midtrans..."; }
  if (alertMsg) alertMsg.innerText = "";

  const firstName = document.getElementById('regFirstName')?.value || '';
  const lastName = document.getElementById('regLastName')?.value || '';
  const fullName = (firstName + ' ' + lastName).trim();
  const email = document.getElementById('regEmail')?.value || '';

  const activeBtn = document.querySelector('.pay-method-btn.active');
  let payMethod = 'credit_card';

  if (activeBtn) {
    const btnText = activeBtn.innerText.toLowerCase();
    if (btnText.includes('e-wallet')) {
      const ewalletSelect = document.getElementById('regEwalletType');
      payMethod = ewalletSelect ? ewalletSelect.value : 'other_qris';
    } else if (btnText.includes('bank')) {
      const bankSelect = document.getElementById('regBankType');
      payMethod = bankSelect ? bankSelect.value : 'bca_va';
    } else {
      payMethod = 'credit_card';
    }
  }

  // Pengecekan cerdas: Apakah user yang login ini sedang melakukan upgrade untuk emailnya sendiri?
  const isUpgrading = (globalUserData && globalUserData.email === email) ? true : false;

  fetch('/api/create-transaction', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: fullName,
      email: email,
      plan: selectedPlanName,
      price: selectedPlanPrice,
      method: payMethod,
      isUpgrading: isUpgrading
    })
  })
  .then(res => res.json())
  .then(data => {
    if (btn) { btn.disabled = false; btn.innerText = "💳 Bayar Sekarang"; }
    
    if (data.success && data.token) {
      lastSnapToken = data.token;
      localStorage.setItem('automedia_snap_token', data.token);

      if (window.snap) {
        showToast("Membuka Pop-Up Pembayaran Midtrans...", "#6366f1");

        window.snap.pay(data.token, {
          onSuccess: function(result) {
            showToast("🎉 Pembayaran Berhasil Diproses!", "#34d399");
            localStorage.removeItem('automedia_snap_token');
            lastSnapToken = null;
            onCheckoutSuccess(data, email, fullName, isUpgrading);
          },
          onPending: function(result) {
            showToast("⏳ Menunggu konfirmasi pembayaran...", "#f59e0b");
            onCheckoutSuccess(data, email, fullName, isUpgrading);
          },
          onError: function(result) {
            showToast("✕ Transaksi pembayaran gagal.", "#ef4444");
          },
          onClose: function() {
            showToast("Pop-up pembayaran ditutup. Anda dapat membukanya kembali via Dashboard.", "#9ca3af");
            onCheckoutSuccess(data, email, fullName, isUpgrading);
          }
        });
      } else {
        showToast("Error: Script Midtrans Snap belum ter-load", "#ef4444");
      }
    } else {
      // Jika error karena deteksi email ganda dari backend
      if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = data.message || "Gagal terhubung ke gateway pembayaran."; }
      showToast(data.message || "Error Midtrans", "#ef4444");
    }
  })
  .catch(err => {
    if (btn) { btn.disabled = false; btn.innerText = "💳 Bayar Sekarang"; }
    if (alertMsg) { alertMsg.style.color = '#ef4444'; alertMsg.innerText = "Server Timeout: " + err; }
  });
}

function reopenSnapPayment() {
  const storedToken = lastSnapToken || localStorage.getItem('automedia_snap_token');
  
  if (storedToken && window.snap) {
    showToast("Membuka kembali Pop-Up Pembayaran Midtrans...", "#6366f1");

    window.snap.pay(storedToken, {
      onSuccess: function(result) {
        showToast("🎉 Pembayaran Berhasil Diproses!", "#34d399");
        localStorage.removeItem('automedia_snap_token');
        lastSnapToken = null;

        if (globalUserData) {
          globalUserData.isPaid = true;
          globalUserData.status = 'Active Subscriber ($97/mo)';
          localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
          if (typeof renderLoggedInUI === 'function') renderLoggedInUI(globalUserData, true);
        }
      },
      onPending: function(result) {
        showToast("⏳ Menunggu konfirmasi pembayaran...", "#f59e0b");
      },
      onError: function(result) {
        showToast("✕ Transaksi pembayaran gagal.", "#ef4444");
      },
      onClose: function() {
        showToast("Pop-up pembayaran ditutup. Klik kembali untuk membuka.", "#9ca3af");
      }
    });
  } else {
    if (typeof openUpgradePayment === 'function') openUpgradePayment();
  }
}

function onCheckoutSuccess(res, email, fullName, isUpgrading = false) {
  if (isUpgrading) {
    globalUserData.isPaid = true;
    globalUserData.status = 'Active Subscriber ($97/mo)';
    localStorage.setItem('automedia_user', JSON.stringify(globalUserData));
    
    if (typeof renderLoggedInUI === 'function') renderLoggedInUI(globalUserData, true);
    showToast("🎉 Pembayaran Berhasil! API Key Anda Terbuka!", "#34d399");
    
    // Redirect instan ke dashboard khusus jika sedang upgrade
    if (window.location.pathname === '/checkout') {
      window.location.href = '/dashboard';
    }
    return;
  }

  // Jika user baru yang memaksakan bayar langsung (tanpa tombol trial)
  globalUserData = { 
    name: fullName, 
    email: email, 
    apiKey: '-', 
    isPaid: false,
    status: 'Pending Payment (Menunggu Konfirmasi)' 
  };
  localStorage.setItem('automedia_user', JSON.stringify(globalUserData));

  document.getElementById('modalStepForm').style.display = 'none';
  document.getElementById('modalStepSurvey').style.display = 'block';
  if (typeof renderLoggedInUI === 'function') renderLoggedInUI(globalUserData, false);
}

window.startPaymentStatusPolling = startPaymentStatusPolling;
window.stopPaymentStatusPolling = stopPaymentStatusPolling;
window.selectPayMethod = selectPayMethod;
window.initCardDetection = initCardDetection;
window.handleFreeTrial = handleFreeTrial;
window.handleCheckoutSubmit = handleCheckoutSubmit;
window.reopenSnapPayment = reopenSnapPayment;