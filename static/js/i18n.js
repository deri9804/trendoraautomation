/**
 * Trendora Internationalization (i18n) Engine
 * Standard English (US) <-> Bahasa Indonesia Switcher
 * Persists in localStorage and supports URL query parameter: ?lang=en / ?lang=id
 */

(function () {
  const I18N = {
    en: {
      // Topbar & Nav
      nav_features: "Features",
      nav_platforms: "Platforms",
      nav_n8n_docs: "n8n Node",
      nav_pricing: "Pricing",
      nav_faq: "FAQ",
      nav_contact: "Contact",
      nav_dashboard: "User Dashboard",
      nav_landing: "Landing Page / Web",
      nav_login: "Log In",
      nav_register: "Get Started Free 🚀",
      nav_logout: "Log Out 🚪",

      // Sidebar
      sidebar_collapse: "Collapse Menu",
      sidebar_expand: "Expand Menu",
      sidebar_main_nav: "MAIN NAVIGATION",
      sidebar_overview: "Overview / Dashboard",
      sidebar_integration: "n8n Integration & API",
      sidebar_social: "Social Media Accounts",
      sidebar_omnichannel: "Omnichannel AI Suite",
      sidebar_calendar: "Content Calendar",
      sidebar_ig_dm: "Instagram Auto DM",
      sidebar_studio: "Studio Publisher",
      sidebar_fb: "Facebook (Reels & Page)",
      sidebar_ig: "Instagram (Reels)",
      sidebar_yt: "YouTube (Shorts)",
      sidebar_tiktok: "TikTok (Direct Post)",
      sidebar_twitter: "Twitter / X",
      sidebar_linkedin: "LinkedIn",
      sidebar_threads: "Threads",
      sidebar_multi: "Multi-Broadcast",
      sidebar_logs: "Activity Logs & History",
      sidebar_settings: "SETTINGS & SUPPORT",
      sidebar_upgrade: "Subscription (Upgrade)",
      sidebar_api_doc: "API Documentation",
      sidebar_whatsapp: "WhatsApp Support",
      sidebar_ecosystem_label: "OTHER SERVICES (ECOSYSTEM)",
      sidebar_logout: "Log Out",

      // TikTok Privacy Tips Alert
      tiktok_tip_title: "💡 TikTok Creator Account Setup Tips:",
      tiktok_tip_body: 'If your video uploads in <code style="background: rgba(0,0,0,0.3); color: #f59e0b; padding: 2px 6px; border-radius: 4px;">Only Me (Self Only)</code> status even though set to <strong>Public</strong> in n8n / dashboard, check your TikTok mobile app profile. Ensure that <strong>Private Account</strong> is toggled off (Go to TikTok &gt; Profile &gt; Settings &amp; Privacy &gt; Privacy &gt; disable <em>Private Account</em>). Official TikTok API locks uploads to \'Only Me\' by default if the creator profile is set to private.',

      // Overview Tab
      overview_greeting: "Hello",
      overview_greeting_sub: "Multi-Channel Automation Engine",
      overview_btn_n8n: "⚡ n8n Integration",
      overview_btn_studio: "🎬 Studio Publisher",
      overview_stat_total: "Total Videos Processed",
      overview_stat_total_sub: "Auto-publishing history",
      overview_stat_success: "Success Rate",
      overview_stat_success_sub: "All requests delivered",
      overview_stat_channels: "Active Social Channels",
      overview_stat_channels_sub: "TikTok, Meta & Others",
      overview_stat_license: "License Status",
      overview_stat_license_sub: "Active plan",

      // Integration Tab
      integration_title: "⚡ n8n, Make & REST API Integration Hub",
      integration_subtitle: "Use the API Key credentials and Webhook endpoint below to connect your n8n workflow to all social media automatically.",
      integration_target_url: "Target POST URL (n8n HTTP Request):",
      integration_copy_btn: "📋 Copy Webhook URL",
      integration_docs_btn: "📖 Open Interactive Documentation →",

      // Social Accounts Page
      social_badge: "CONNECTED CHANNELS",
      social_title: "📱 Connected Social Media Channels",
      social_subtitle: "Connect your social media accounts via official OAuth2 authorization. Scheduled posts from n8n and Studio Publisher are automatically dispatched to active accounts.",
      social_quota_title: "📊 Social Media Account Quotas:",
      social_quota_used: "Slots Used",
      social_refresh_btn: "🔄 Refresh Accounts",
      social_not_connected: "○ Not Connected",
      social_active: "● Active Account",
      social_active_plural: "● Active Accounts",
      social_disconnect: "✕ Disconnect",
      social_connect: "🔗 Connect",
      social_add_account: "+ Add Account",
      social_empty_channel: "No account connected yet.",
      social_trial_info: "Free Trial Plan (1 Profile / Platform)",
      social_unlimited_info: "Flexible slot allocation: You can connect up to 100 accounts simultaneously (e.g. multiple Facebook Pages, TikTok, or multi-platform combinations).",

      // Studio Publisher
      studio_fb_badge: "FACEBOOK CONTENT SHARING & REELS STUDIO",
      studio_fb_title: "Direct Share to Facebook Reels & Page",
      studio_fb_subtitle: "Select a video, preview live in 9:16 vertical smartphone frame, optimize with AI Hook & Caption, and publish officially to your Facebook Page & Reels.",
      studio_select_page: "📘 Select Target Facebook Page *",
      studio_refresh_pages: "🔄 Refresh Pages",
      studio_no_page_connected: "-- No Facebook Page connected yet --",
      studio_page_note: "Reels videos and posts will be published officially to your selected Facebook Page via Meta Graph API.",
      studio_mode_file: "📁 Upload Video File",
      studio_mode_url: "🔗 Input Video URL",
      studio_choose_file: "Choose Video File (.MP4 / .MOV)",
      studio_file_sub: "Up to 500MB (.MP4, .MOV, .WebM) — Supports Full HD & 4K video",
      studio_preview_title: "9:16 Smartphone Preview",
      studio_preview_sub: "Select or upload a video file above to view live preview simulation before publishing.",
      studio_ai_topic_placeholder: "Enter video topic (e.g. Business Automation Secrets in 2026)...",
      studio_ai_btn: "Generate AI Hook",
      studio_ai_multivar_btn: "🎯 Generate 4 Angles (Multi-Angle Hook)",
      studio_ai_multivar_sub: "Automatically generates distinct hooks to avoid duplicate content flags",
      studio_ai_var_header: "✨ Choose Hook & Caption Variation:",
      studio_ai_var_hint: "Click card to apply",
      studio_video_title: "🏷️ Video Title *",
      studio_title_placeholder: "Enter compelling video title with high CTR...",
      studio_caption_label: "📝 Video Caption / Description",
      studio_caption_placeholder: "Write an engaging caption for your video... Include hashtags to reach audiences organically.",
      studio_quick_hashtags: "Quick Hashtags:",
      studio_fb_format_label: "🎯 Meta Content Distribution Format",
      studio_fb_format_reels: "🌟 Facebook Reels (9:16 Vertical Format - Maximum Organic Reach)",
      studio_fb_format_feed: "📹 Standard Page Feed Video",
      studio_shield_title: "Smart Multi-Account Shield (Anti-Duplicate & Anti-Spam)",
      studio_shield_badge: "SAFE ALGORITHM",
      studio_spinner_label: "⚡ Auto-Video Spinner (Unique File Hash)",
      studio_spinner_badge: "ACTIVE",
      studio_spinner_sub: "Automatically rotates MP4 atoms & binary hash so each account receives a unique file, preventing \"Unoriginal Content\" penalties.",
      studio_dist_mode_label: "⏱️ Publishing Timeline Mode (Anti-Blast Spam)",
      studio_dist_imm: "⚡ Publish Immediately",
      studio_dist_stag: "🛡️ Staggered Distribution (Safe)",
      studio_dist_stag_select: "Select Random Delay Range:",
      studio_dist_stag_preview: "ℹ️ First account publishes immediately. Subsequent accounts are scheduled with random intervals to simulate organic activity.",
      studio_schedule_toggle: "📅 Schedule for Later (Auto-Publish)",
      studio_schedule_sub: "Add to Content Calendar queue and auto-post at peak audience hours.",
      studio_schedule_time_label: "Select Date & Time (WIB):",
      studio_schedule_peak_label: "Recommended Peak Hours:",
      studio_publish_now: "🚀 Publish to Facebook Reels Now",
      studio_publish_btn_generic: "🚀 Publish Content Now",
      studio_share_tooltip: "Please select or upload a video file first.",
      studio_notice_select_video: "⚠️ Please select or upload a video file above before publishing.",
      studio_notice_after_publish: "ℹ️ Once published, platform servers will process high-definition video before rendering on your page feed.",
      studio_publishing_in_progress: "Publishing to Facebook Reels...",
      studio_preparing_video: "Preparing video file and validating account authorization...",
      studio_publish_success: "Video Successfully Published!",
      studio_publish_success_sub: "Your video has been published to the platform via official API authorization.",
      studio_modal_dest_label: "Destination Account / Page:",
      studio_modal_time_label: "Publication Time:",
      studio_modal_success_explain: "📌 <strong>Publication Confirmed:</strong> Video was successfully delivered to platform servers. <em>Platform systems require a few seconds to process high-definition video before appearing on your public feed.</em>",
      studio_modal_success_open_btn: "Watch Reel on Facebook",
      studio_modal_success_fbtab_btn: "Open Facebook Page Videos Tab",
      studio_modal_success_close_btn: "Close & Create New Post"
    },
    id: {
      // Topbar & Nav
      nav_features: "Fitur",
      nav_platforms: "Platform",
      nav_n8n_docs: "n8n Node",
      nav_pricing: "Harga",
      nav_faq: "FAQ",
      nav_contact: "Kontak",
      nav_dashboard: "User Dashboard",
      nav_landing: "Landing Page / Web",
      nav_login: "Log In",
      nav_register: "Daftar Gratis 🚀",
      nav_logout: "Keluar 🚪",

      // Sidebar
      sidebar_collapse: "Tutup Menu",
      sidebar_expand: "Buka Menu",
      sidebar_main_nav: "NAVIGASI UTAMA",
      sidebar_overview: "Ringkasan / Beranda",
      sidebar_integration: "Integrasi n8n & API",
      sidebar_social: "Akun Sosial Media",
      sidebar_omnichannel: "Omnichannel AI Suite",
      sidebar_calendar: "Kalender Konten",
      sidebar_ig_dm: "Instagram Auto DM",
      sidebar_studio: "Studio Publisher",
      sidebar_fb: "Facebook (Reels & Page)",
      sidebar_ig: "Instagram (Reels)",
      sidebar_yt: "YouTube (Shorts)",
      sidebar_tiktok: "TikTok (Direct Post)",
      sidebar_twitter: "Twitter / X",
      sidebar_linkedin: "LinkedIn",
      sidebar_threads: "Threads",
      sidebar_multi: "Multi-Broadcast",
      sidebar_logs: "Log & Riwayat",
      sidebar_settings: "PENGATURAN & BANTUAN",
      sidebar_upgrade: "Langganan (Upgrade)",
      sidebar_api_doc: "Dokumentasi API",
      sidebar_whatsapp: "Bantuan WhatsApp",
      sidebar_ecosystem_label: "LAYANAN LAINNYA (ECOSYSTEM)",
      sidebar_logout: "Keluar Akun",

      // TikTok Privacy Tips Alert
      tiktok_tip_title: "💡 Tips Pengaturan Akun TikTok Creator:",
      tiktok_tip_body: 'Jika video ter-upload dalam status <code style="background: rgba(0,0,0,0.3); color: #f59e0b; padding: 2px 6px; border-radius: 4px;">Hanya Saya (Self Only)</code> meskipun setelan di n8n / dashboard sudah <strong>Public</strong>, periksa profil TikTok Anda di aplikasi HP. Pastikan toggle <strong>Akun Privat</strong> dinonaktifkan (Buka TikTok &gt; Profil &gt; Pengaturan &amp; Privasi &gt; Privasi &gt; matikan <em>Akun Privat</em>). API resmi TikTok secara default mengunci upload ke \'Hanya Saya\' jika akun kreator disetel privat.',

      // Overview Tab
      overview_greeting: "Halo",
      overview_greeting_sub: "Multi-Channel Automation Engine",
      overview_btn_n8n: "⚡ Integrasi n8n",
      overview_btn_studio: "🎬 Studio Publisher",
      overview_stat_total: "Total Video Diproses",
      overview_stat_total_sub: "Riwayat posting otomatis",
      overview_stat_success: "Tingkat Keberhasilan",
      overview_stat_success_sub: "Semua request terkirim",
      overview_stat_channels: "Sosial Media Aktif",
      overview_stat_channels_sub: "TikTok, Meta & Lainnya",
      overview_stat_license: "Status Lisensi",
      overview_stat_license_sub: "Fitur aktif",

      // Integration Tab
      integration_title: "⚡ Pusat Integrasi n8n, Make & REST API",
      integration_subtitle: "Gunakan kredensial API Key dan endpoint Webhook di bawah untuk menghubungkan workflow n8n Anda ke seluruh sosial media secara otomatis.",
      integration_target_url: "Target POST URL (n8n HTTP Request):",
      integration_copy_btn: "📋 Salin URL Webhook",
      integration_docs_btn: "📖 Buka Halaman Dokumentasi Interaktif →",

      // Social Accounts Page
      social_badge: "CONNECTED CHANNELS",
      social_title: "📱 Saluran Sosial Media Terhubung",
      social_subtitle: "Hubungkan akun sosial media Anda melalui otorisasi resmi OAuth2. Postingan dari n8n otomatis dikirimkan ke akun yang aktif.",
      social_quota_title: "📊 Kuota Slot Akun Medsos:",
      social_quota_used: "Slot Terpakai",
      social_refresh_btn: "🔄 Segarkan Data Akun",
      social_not_connected: "○ Belum Terhubung",
      social_active: "● Akun Aktif",
      social_active_plural: "● Akun Aktif",
      social_disconnect: "✕ Putuskan",
      social_connect: "🔗 Hubungkan",
      social_add_account: "+ Tambah Akun",
      social_empty_channel: "Belum ada akun terhubung.",
      social_trial_info: "Paket FREE TRIAL (1 Akun / Platform)",
      social_unlimited_info: "Slot bebas dialokasikan: Anda bisa menghubungkan hingga 100 akun sekaligus (misal 100 TikTok atau kombinasi platform lainnya).",

      // Studio Publisher
      studio_fb_badge: "FACEBOOK CONTENT SHARING & REELS STUDIO",
      studio_fb_title: "Direct Share to Facebook Reels",
      studio_fb_subtitle: "Pilih video, lihat pratinjau live smartphone 9:16, optimasi dengan AI Hook & Caption, lalu bagikan secara resmi ke Facebook Page & Reels Anda.",
      studio_select_page: "📘 Pilih Facebook Page Tujuan *",
      studio_refresh_pages: "🔄 Refresh Halaman",
      studio_no_page_connected: "-- Belum ada Facebook Page terhubung --",
      studio_page_note: "Video Reels akan dipublikasikan secara resmi ke Halaman Facebook yang Anda pilih melalui Graph API.",
      studio_mode_file: "📁 Unggah Berkas Video",
      studio_mode_url: "🔗 Input URL Video",
      studio_choose_file: "Pilih Berkas Video (.MP4 / .MOV)",
      studio_file_sub: "Maksimal 500MB (.MP4, .MOV, .WebM) — Mendukung video Full HD & 4K",
      studio_preview_title: "Pratinjau Smartphone 9:16",
      studio_preview_sub: "Pilih atau unggah file video di atas untuk melihat simulasi pratinjau live sebelum dipublikasikan.",
      studio_ai_topic_placeholder: "Ketik topik video (contoh: Rahasia Otomasi Bisnis)...",
      studio_ai_btn: "Buatkan Hook AI",
      studio_ai_multivar_btn: "🎯 Buat 4 Variasi Sudut Pandang (Multi-Angle Hook)",
      studio_ai_multivar_sub: "Otomatis buat hook berbeda agar tidak dianggap konten duplikat",
      studio_ai_var_header: "✨ Pilih Variasi Hook & Caption:",
      studio_ai_var_hint: "Klik kartu untuk menerapkan",
      studio_video_title: "🏷️ Judul Video (Title) *",
      studio_title_placeholder: "Masukkan judul menarik dengan Click-Through-Rate tinggi...",
      studio_caption_label: "📝 Deskripsi / Caption Video",
      studio_caption_placeholder: "Tulis caption menarik untuk video Anda... Sertakan hashtag untuk menjangkau audiens secara organik.",
      studio_quick_hashtags: "Hashtag Cepat:",
      studio_fb_format_label: "🎯 Format Distribusi Konten Meta",
      studio_fb_format_reels: "🌟 Facebook Reels (Format Vertikal 9:16 - Jangkauan Organik Maksimal)",
      studio_fb_format_feed: "📹 Video Postingan Standar Halaman",
      studio_shield_title: "Smart Multi-Account Shield (Anti-Duplikasi & Anti-Spam)",
      studio_shield_badge: "ALGORITMA AMAN",
      studio_spinner_label: "⚡ Auto-Video Spinner (File Hash Unik)",
      studio_spinner_badge: "AKTIF",
      studio_spinner_sub: "Otomatis memodifikasi atom MP4 & hash biner agar setiap akun menerima berkas unik, mencegah penalti konten tidak orisinal.",
      studio_dist_mode_label: "⏱️ Mode Distribusi Waktu (Anti-Blast Spam)",
      studio_dist_imm: "⚡ Publikasikan Seketika (Serentak)",
      studio_dist_stag: "🛡️ Distribusi Bertahap / Staggered (Aman)",
      studio_dist_stag_select: "Pilih Rentang Jeda Acak:",
      studio_dist_stag_preview: "ℹ️ Akun pertama tayang seketika. Akun berikutnya dijadwalkan otomatis dengan interval acak untuk mensimulasikan aktivitas organik.",
      studio_schedule_toggle: "📅 Jadwalkan untuk Nanti (Auto-Publish)",
      studio_schedule_sub: "Simpan ke antrean Kalender Konten dan posting otomatis di jam audiens paling aktif.",
      studio_schedule_time_label: "Pilih Tanggal & Waktu Tayang (WIB):",
      studio_schedule_peak_label: "Rekomendasi Jam Ramai:",
      studio_publish_now: "🚀 Publikasikan ke Facebook Reels Sekarang",
      studio_publish_btn_generic: "🚀 Publikasikan Konten Sekarang",
      studio_share_tooltip: "Silakan pilih atau unggah file video terlebih dahulu.",
      studio_notice_select_video: "⚠️ Silakan pilih file video di atas sebelum mempublikasikan.",
      studio_notice_after_publish: "ℹ️ Setelah dipublikasikan, server platform akan memproses resolusi HD dan video akan segera tampil di feed profil Anda.",
      studio_publishing_in_progress: "Mengunggah ke Facebook Reels...",
      studio_preparing_video: "Mempersiapkan berkas video dan memvalidasi otorisasi akun...",
      studio_publish_success: "Video Berhasil Dipublikasikan!",
      studio_publish_success_sub: "Video Anda telah sukses diposting ke platform melalui otorisasi resmi API.",
      studio_modal_dest_label: "Akun / Halaman Tujuan:",
      studio_modal_time_label: "Waktu Publikasi:",
      studio_modal_success_explain: "📌 <strong>Konfirmasi Publikasi:</strong> Video telah berhasil dikirim ke server platform. <em>Setelah dipublikasikan, sistem platform memerlukan beberapa detik untuk memproses resolusi video sebelum muncul di beranda publik.</em>",
      studio_modal_success_open_btn: "Tonton Reel di Facebook",
      studio_modal_success_fbtab_btn: "Buka Tab Video Halaman Facebook",
      studio_modal_success_close_btn: "Tutup & Buat Postingan Baru"
    }
  };

  // Determine initial language: URL param > localStorage > DEFAULT EN (English US)
  function getInitialLanguage() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const urlLang = urlParams.get('lang');
      if (urlLang === 'id' || urlLang === 'en') return urlLang;

      const storedLang = localStorage.getItem('trendora_lang');
      if (storedLang === 'id' || storedLang === 'en') return storedLang;
    } catch (e) {}
    // Default to 'en' (English US) as requested for Meta Review
    return 'en';
  }

  let currentLang = getInitialLanguage();
  window.currentLanguage = currentLang;
  window.I18N = I18N;

  window.t = function (key, fallback) {
    const dict = I18N[window.currentLanguage] || I18N['en'];
    return dict[key] || fallback || key;
  };

  function updateDomLanguage(lang) {
    document.documentElement.lang = (lang === 'en' ? 'en-US' : 'id');

    // 1. Update Toggle Button in Navbar
    const flagEl = document.getElementById('langFlagIcon');
    const labelEl = document.getElementById('langLabelText');
    if (flagEl) flagEl.innerText = (lang === 'en' ? '🇺🇸' : '🇮🇩');
    if (labelEl) labelEl.innerText = (lang === 'en' ? 'EN (US)' : 'ID');

    // 2. Navbar Auth Buttons
    const btnSignUp = document.getElementById('btnNavSignUp');
    const btnLogout = document.getElementById('btnNavLogout');
    if (btnSignUp) btnSignUp.innerText = window.t('nav_register', 'Get Started Free 🚀');
    if (btnLogout) btnLogout.innerText = window.t('nav_logout', 'Log Out 🚪');

    // 3. Sidebar Section Labels & Toggle
    const labelMain = document.getElementById('sidebarLabelMainNav');
    const labelSet = document.getElementById('sidebarLabelSettings');
    const labelEco = document.getElementById('sidebarLabelEcosystem');
    if (labelMain) labelMain.innerText = window.t('sidebar_main_nav', 'MAIN NAVIGATION');
    if (labelSet) labelSet.innerText = window.t('sidebar_settings', 'SETTINGS & SUPPORT');
    if (labelEco) labelEco.innerText = window.t('sidebar_ecosystem_label', 'OTHER SERVICES (ECOSYSTEM)');

    const toggleText = document.getElementById('sidebarToggleText');
    if (toggleText) {
      const isHidden = document.body.classList.contains('sidebar-hidden');
      toggleText.innerText = isHidden ? window.t('sidebar_expand', 'Expand Menu') : window.t('sidebar_collapse', 'Collapse Menu');
    }

    const upText = document.getElementById('sidebarUpgradeText');
    if (upText) upText.innerText = window.t('sidebar_upgrade', 'Subscription (Upgrade)');

    const docText = document.getElementById('sidebarApiDocText');
    if (docText) docText.innerText = window.t('sidebar_api_doc', 'API Documentation');

    const waText = document.getElementById('sidebarWaSupportText');
    if (waText) waText.innerText = window.t('sidebar_whatsapp', 'WhatsApp Support');

    const outText = document.getElementById('sidebarLogoutText');
    if (outText) outText.innerText = window.t('sidebar_logout', 'Log Out');

    // Sidebar Tab Buttons
    const tabBtnMap = {
      'overview': 'sidebar_overview',
      'integration': 'sidebar_integration',
      'social': 'sidebar_social',
      'omnichannel': 'sidebar_omnichannel',
      'content-calendar': 'sidebar_calendar',
      'instagram-auto-dm': 'sidebar_ig_dm',
      'tiktok-studio': 'sidebar_studio',
      'logs': 'sidebar_logs'
    };

    Object.entries(tabBtnMap).forEach(([tabKey, transKey]) => {
      const btn = document.querySelector(`.sidebar-tab-btn[data-tab="${tabKey}"] span:first-of-type`);
      if (btn) btn.innerText = window.t(transKey, btn.innerText);
    });

    // Sidebar Studio Submenu (Use span:last-of-type to prevent overwriting icon badges)
    const subBtnMap = {
      'facebook': 'sidebar_fb',
      'instagram': 'sidebar_ig',
      'youtube': 'sidebar_yt',
      'tiktok': 'sidebar_tiktok',
      'twitter': 'sidebar_twitter',
      'linkedin': 'sidebar_linkedin',
      'threads': 'sidebar_threads',
      'multi': 'sidebar_multi'
    };

    Object.entries(subBtnMap).forEach(([platKey, transKey]) => {
      const btn = document.querySelector(`.sidebar-sub-btn[data-studio-plat="${platKey}"] span:last-of-type`);
      if (btn) btn.innerText = window.t(transKey, btn.innerText);
    });

    // 4. TikTok Creator Tips Alert
    const tipTitle = document.getElementById('tiktokTipTitle');
    const tipBody = document.getElementById('tiktokTipBody');
    if (tipTitle) tipTitle.innerHTML = window.t('tiktok_tip_title', '💡 TikTok Creator Account Setup Tips:');
    if (tipBody) tipBody.innerHTML = window.t('tiktok_tip_body', '');

    // 5. Overview Tab
    const greetEl = document.getElementById('dashGreetingText');
    const accPrefix = document.getElementById('dashAccountPrefix');
    if (greetEl) greetEl.innerText = (lang === 'en' ? 'Hello' : 'Halo');
    if (accPrefix) accPrefix.innerText = (lang === 'en' ? 'Account:' : 'Akun:');

    const overN8nBtn = document.querySelector('button[onclick="switchDashboardTab(\'integration\')"] span');
    if (overN8nBtn) overN8nBtn.innerText = window.t('overview_btn_n8n', '⚡ n8n Integration');

    const overStudioBtn = document.querySelector('button[onclick="switchDashboardTab(\'tiktok-studio\')"] span');
    if (overStudioBtn) overStudioBtn.innerText = window.t('overview_btn_studio', '🎬 Studio Publisher');

    const statLabels = document.querySelectorAll('#tab-overview .stat-label');
    const statSubs = document.querySelectorAll('#tab-overview .stat-sub');
    if (statLabels.length >= 4) {
      statLabels[0].innerText = window.t('overview_stat_total', 'Total Videos Processed');
      statLabels[1].innerText = window.t('overview_stat_success', 'Success Rate');
      statLabels[2].innerText = window.t('overview_stat_channels', 'Active Social Channels');
      statLabels[3].innerText = window.t('overview_stat_license', 'License Status');
    }
    if (statSubs.length >= 4) {
      statSubs[0].innerText = window.t('overview_stat_total_sub', 'Auto-publishing history');
      statSubs[1].innerText = window.t('overview_stat_success_sub', 'All requests delivered');
      statSubs[2].innerText = window.t('overview_stat_channels_sub', 'TikTok, Meta & Others');
      statSubs[3].innerText = window.t('overview_stat_license_sub', 'Active plan');
    }

    // 6. Integration Tab
    const integTitle = document.querySelector('#tab-integration h3');
    const integSub = document.querySelector('#tab-integration p');
    if (integTitle) integTitle.innerText = window.t('integration_title', '⚡ n8n, Make & REST API Integration Hub');
    if (integSub) integSub.innerText = window.t('integration_subtitle', 'Use the API Key credentials and Webhook endpoint below to connect your n8n workflow to all social media automatically.');
    const integCopyBtn = document.querySelector('button[onclick="copyWebhookUrl()"]');
    if (integCopyBtn) integCopyBtn.innerText = window.t('integration_copy_btn', '📋 Copy Webhook URL');
    const integDocsBtn = document.querySelector('#tab-integration a[href="/webhook"]');
    if (integDocsBtn) integDocsBtn.innerText = window.t('integration_docs_btn', '📖 Open Interactive Documentation →');

    // 7. Social Accounts Heading
    const socTitle = document.querySelector('#tab-social h3');
    const socSub = document.querySelector('#tab-social p');
    if (socTitle) socTitle.innerText = window.t('social_title', '📱 Connected Social Media Channels');
    if (socSub) socSub.innerText = window.t('social_subtitle', 'Connect your social media accounts via official OAuth2 authorization.');

    // 8. Studio Controls
    const fbLabel = document.querySelector('label[for="studioFbPageSelect"]');
    if (fbLabel) fbLabel.innerHTML = `📘 ${window.t('studio_select_page', 'Select Target Facebook Page')} <span style="color:#1877f2;">*</span>`;

    const fbRefreshBtn = document.querySelector('#studioFieldsFacebook button');
    if (fbRefreshBtn) fbRefreshBtn.innerText = window.t('studio_refresh_pages', '🔄 Refresh Pages');

    const fbNote = document.querySelector('#studioFieldsFacebook p');
    if (fbNote) fbNote.innerText = window.t('studio_page_note', 'Reels videos will be published officially to your selected Facebook Page via Meta Graph API.');

    const btnFile = document.getElementById('btnModeUploadFile');
    const btnUrl = document.getElementById('btnModeInputUrl');
    if (btnFile) btnFile.innerText = window.t('studio_mode_file', '📁 Upload Video File');
    if (btnUrl) btnUrl.innerText = window.t('studio_mode_url', '🔗 Input Video URL');

    const chooseFileTitle = document.querySelector('#boxVideoFileInput div[style*="font-weight: 700"]');
    const chooseFileSub = document.querySelector('#boxVideoFileInput div[style*="font-size: 11px"]');
    if (chooseFileTitle) chooseFileTitle.innerText = window.t('studio_choose_file', 'Choose Video File (.MP4 / .MOV)');
    if (chooseFileSub) chooseFileSub.innerText = window.t('studio_file_sub', 'Up to 500MB (.MP4, .MOV, .WebM) — Supports Full HD & 4K video');

    // Studio Controls continued
    const aiTopicInput = document.getElementById('studioAiTopicInput');
    if (aiTopicInput) aiTopicInput.placeholder = window.t('studio_ai_topic_placeholder', 'Enter video topic (e.g. Business Automation Secrets in 2026)...');

    const aiBtnText = document.getElementById('studioAiBtnText');
    if (aiBtnText) aiBtnText.innerText = window.t('studio_ai_btn', 'Generate AI Hook');

    const aiMultiVar = document.getElementById('studioAiMultiVarText');
    if (aiMultiVar) aiMultiVar.innerText = window.t('studio_ai_multivar_btn', '🎯 Generate 4 Angles (Multi-Angle Hook)');

    const aiMultiSub = document.getElementById('studioAiMultiVarSub');
    if (aiMultiSub) aiMultiSub.innerText = window.t('studio_ai_multivar_sub', 'Automatically generates distinct hooks to avoid duplicate content flags');

    const aiVarHead = document.getElementById('studioAiVariationsHeader');
    if (aiVarHead) aiVarHead.innerText = window.t('studio_ai_var_header', '✨ Choose Hook & Caption Variation:');

    const aiVarHint = document.getElementById('studioAiVariationsHint');
    if (aiVarHint) aiVarHint.innerText = window.t('studio_ai_var_hint', 'Click card to apply');

    const labelTitle = document.getElementById('studioLabelVideoTitle');
    if (labelTitle) labelTitle.innerHTML = `${window.t('studio_video_title', '🏷️ Video Title *')} <span style="color: #ff0000;">*</span>`;

    const ytTitleInput = document.getElementById('studioYtTitleInput');
    if (ytTitleInput) ytTitleInput.placeholder = window.t('studio_title_placeholder', 'Enter compelling video title with high CTR...');

    const captionLabel = document.querySelector('label[for="tiktokCaptionInput"]');
    if (captionLabel) captionLabel.innerText = window.t('studio_caption_label', '📝 Video Caption / Description');

    const captionInput = document.getElementById('tiktokCaptionInput');
    if (captionInput) captionInput.placeholder = window.t('studio_caption_placeholder', 'Write an engaging caption for your video...');

    const quickHashLabel = document.getElementById('studioQuickHashtagsLabel');
    if (quickHashLabel) quickHashLabel.innerText = window.t('studio_quick_hashtags', 'Quick Hashtags:');

    const fbFormatLabel = document.getElementById('studioFbFormatLabel');
    if (fbFormatLabel) fbFormatLabel.innerText = window.t('studio_fb_format_label', '🎯 Meta Content Distribution Format');

    const fbFormatSelect = document.getElementById('studioFbFormatSelect');
    if (fbFormatSelect && fbFormatSelect.options.length >= 2) {
      fbFormatSelect.options[0].text = window.t('studio_fb_format_reels', '🌟 Facebook Reels (9:16 Vertical Format - Maximum Organic Reach)');
      fbFormatSelect.options[1].text = window.t('studio_fb_format_feed', '📹 Standard Page Feed Video');
    }

    const shieldTitle = document.getElementById('studioShieldTitle');
    const shieldBadge = document.getElementById('studioShieldBadge');
    if (shieldTitle) shieldTitle.innerText = window.t('studio_shield_title', 'Smart Multi-Account Shield (Anti-Duplicate & Anti-Spam)');
    if (shieldBadge) shieldBadge.innerText = window.t('studio_shield_badge', 'SAFE ALGORITHM');

    const spinnerLabel = document.getElementById('studioSpinnerLabel');
    const spinnerBadge = document.getElementById('studioSpinnerBadge');
    const spinnerSub = document.getElementById('studioSpinnerSub');
    if (spinnerLabel) spinnerLabel.innerText = window.t('studio_spinner_label', '⚡ Auto-Video Spinner (Unique File Hash)');
    if (spinnerBadge) spinnerBadge.innerText = (lang === 'en' ? 'ACTIVE' : 'AKTIF');
    if (spinnerSub) spinnerSub.innerText = window.t('studio_spinner_sub', 'Automatically rotates MP4 atoms & binary hash so each account receives a unique file, preventing "Unoriginal Content" penalties.');

    const distLabel = document.getElementById('studioDistModeLabel');
    const immLabel = document.getElementById('studioDistImmLabel');
    const stagLabel = document.getElementById('studioDistStagLabel');
    const stagSelectLabel = document.getElementById('studioStaggerSelectLabel');
    const stagPreview = document.getElementById('studioStaggerPreviewNote');
    if (distLabel) distLabel.innerText = window.t('studio_dist_mode_label', '⏱️ Publishing Timeline Mode (Anti-Blast Spam)');
    if (immLabel) immLabel.innerText = window.t('studio_dist_imm', '⚡ Publish Immediately');
    if (stagLabel) stagLabel.innerText = window.t('studio_dist_stag', '🛡️ Staggered Distribution (Safe)');
    if (stagSelectLabel) stagSelectLabel.innerText = window.t('studio_dist_stag_select', 'Select Random Delay Range:');
    if (stagPreview) stagPreview.innerText = window.t('studio_dist_stag_preview', 'ℹ️ First account publishes immediately. Subsequent accounts are scheduled with random intervals to simulate organic activity.');

    const schedLabel = document.getElementById('studioScheduleToggleLabel');
    const schedSub = document.getElementById('studioScheduleToggleSub');
    const schedPickerLabel = document.getElementById('studioSchedulePickerLabel');
    const peakLabel = document.getElementById('studioSchedulePeakHoursLabel');
    if (schedLabel) schedLabel.innerText = window.t('studio_schedule_toggle', '📅 Schedule for Later (Auto-Publish)');
    if (schedSub) schedSub.innerText = window.t('studio_schedule_sub', 'Add to Content Calendar queue and auto-post at peak audience hours.');
    if (schedPickerLabel) schedPickerLabel.innerText = window.t('studio_schedule_time_label', 'Select Date & Time (WIB):');
    if (peakLabel) peakLabel.innerText = window.t('studio_schedule_peak_label', 'Recommended Peak Hours:');

    const shareTooltip = document.getElementById('tiktokShareTooltipText');
    const shareNotice = document.getElementById('tiktokShareNotice');
    const shareSubNotice = document.getElementById('tiktokShareSubNotice');
    if (shareTooltip) shareTooltip.innerText = window.t('studio_share_tooltip', 'Please select or upload a video file first.');
    if (shareNotice && shareNotice.innerText.includes('video')) {
      shareNotice.innerText = window.t('studio_notice_select_video', '⚠️ Please select or upload a video file above before publishing.');
    }
    if (shareSubNotice) shareSubNotice.innerText = window.t('studio_notice_after_publish', 'ℹ️ Once published, platform servers will process high-definition video before rendering on your page feed.');

    // 9. Modals Language Sync
    const progModalTitle = document.getElementById('studioProgressModalTitle');
    const progStatusText = document.getElementById('tiktokUploadStatusText');
    if (progModalTitle) progModalTitle.innerText = window.t('studio_modal_progress_title', 'Publishing to Facebook Reels...');
    if (progStatusText && (progStatusText.innerText.includes('Memvalidasi') || progStatusText.innerText.includes('Validating'))) {
      progStatusText.innerText = window.t('studio_modal_progress_step1', 'Preparing video file and validating account authorization...');
    }

    const succTitle = document.getElementById('studioSuccessModalTitle');
    const succSub = document.getElementById('studioSuccessModalSubtitle');
    const succDestLabel = document.getElementById('studioSuccessDestLabel');
    const succTimeLabel = document.getElementById('studioSuccessTimeLabel');
    const succExplain = document.getElementById('studioSuccessExplainBox');
    const succOpenText = document.getElementById('studioSuccessOpenBtnText');
    const succFbTabText = document.getElementById('studioSuccessFbTabBtnText');
    const succCloseBtn = document.getElementById('studioSuccessCloseBtn');

    if (succTitle) succTitle.innerText = window.t('studio_publish_success', 'Video Successfully Published!');
    if (succSub) succSub.innerText = window.t('studio_publish_success_sub', 'Your video has been published to the platform via official API authorization.');
    if (succDestLabel) succDestLabel.innerText = window.t('studio_modal_dest_label', 'Destination Account / Page:');
    if (succTimeLabel) succTimeLabel.innerText = window.t('studio_modal_time_label', 'Publication Time:');
    if (succExplain) succExplain.innerHTML = window.t('studio_modal_success_explain', '📌 <strong>Publication Confirmed:</strong> Video was successfully delivered to platform servers.');
    if (succOpenText) succOpenText.innerText = window.t('studio_modal_success_open_btn', 'Watch Reel on Facebook');
    if (succFbTabText) succFbTabText.innerText = window.t('studio_modal_success_fbtab_btn', 'Open Facebook Page Videos Tab');
    if (succCloseBtn) succCloseBtn.innerText = window.t('studio_modal_success_close_btn', 'Close & Create New Post');

    // 10. Phone Preview Placeholder
    const phTitle = document.getElementById('studioPlaceholderTitle');
    if (phTitle) phTitle.innerText = window.t('studio_preview_title', '9:16 Smartphone Preview');
    const metaDisplay = document.getElementById('tiktokVideoMetaDisplay');
    if (metaDisplay && (metaDisplay.innerText === 'Belum ada video dipilih' || metaDisplay.innerText === 'No video selected')) {
      metaDisplay.innerText = (lang === 'en' ? 'No video selected' : 'Belum ada video dipilih');
    }

    // Refresh Studio platform UI if available
    if (typeof window.switchStudioPlatform === 'function') {
      window.switchStudioPlatform(window.currentStudioPlatform || 'facebook');
    } else if (typeof window.updateStudioStatus === 'function') {
      window.updateStudioStatus(window.currentStudioPlatform || 'facebook');
    }

    // Re-render social channels if function exists
    if (typeof window.renderSocialChannels === 'function') {
      window.renderSocialChannels();
    }
  }

  window.setLanguage = function (lang) {
    if (lang !== 'en' && lang !== 'id') lang = 'en';
    currentLang = lang;
    window.currentLanguage = lang;
    try {
      localStorage.setItem('trendora_lang', lang);
    } catch (e) {}
    updateDomLanguage(lang);
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang } }));
  };

  window.toggleLanguage = function () {
    const nextLang = (window.currentLanguage === 'en' ? 'id' : 'en');
    window.setLanguage(nextLang);
  };

  // Run on DOM ready
  document.addEventListener('DOMContentLoaded', function () {
    updateDomLanguage(window.currentLanguage);
  });
})();
