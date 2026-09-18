/* ════════════════════════════════════════════════
   CYBER RISK INTELLIGENCE SYSTEM — JS
   Gauge animation, theme toggle, report generation,
   feature bars, page transitions
   ════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    // ─── THEME TOGGLE ───
    const root = document.documentElement;
    const themeIcon = document.getElementById('themeIcon');
    const themeToggle = document.getElementById('themeToggle');
    const settingsToggle = document.getElementById('settingsThemeToggle');
    const themeLabel = document.getElementById('themeLabel');

    function getTheme() {
        return localStorage.getItem('cris-theme') || 'light';
    }

    function applyTheme(theme) {
        root.setAttribute('data-theme', theme);
        localStorage.setItem('cris-theme', theme);
        if (themeIcon) themeIcon.textContent = theme === 'dark' ? 'light_mode' : 'dark_mode';
        if (themeLabel) themeLabel.textContent = theme === 'dark' ? 'Dark' : 'Light';
        if (settingsToggle) {
            settingsToggle.classList.toggle('active', theme === 'dark');
        }
    }

    applyTheme(getTheme());

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
        });
    }

    if (settingsToggle) {
        settingsToggle.addEventListener('click', () => {
            applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
        });
    }

    // ─── LOADING OVERLAY ───
    const loadingOverlay = document.getElementById('loadingOverlay');

    const forms = document.querySelectorAll('#urlForm, #mailForm');
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            if (loadingOverlay) loadingOverlay.classList.add('active');
        });
    });

    // ─── GAUGE COUNTER ───
    const gaugeNum = document.getElementById('gaugeNum');
    if (gaugeNum) {
        const target = parseInt(gaugeNum.dataset.target, 10);
        animateCounter(gaugeNum, 0, target, 1200);
    }

    // ─── FEATURE BAR FILLS ───
    const featureBars = document.querySelectorAll('.feat-bar-fill');
    if (featureBars.length) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const bar = entry.target;
                    const imp = parseFloat(bar.dataset.importance) || 0;
                    const w = Math.min(imp * 3.5, 100);
                    setTimeout(() => { bar.style.width = w + '%'; }, 200);
                    observer.unobserve(bar);
                }
            });
        }, { threshold: 0.15 });
        featureBars.forEach(bar => observer.observe(bar));
    }

    // ─── CONFIDENCE BAR ───
    const confBars = document.querySelectorAll('.conf-bar-fill');
    confBars.forEach(bar => {
        const w = parseFloat(bar.dataset.width) || 0;
        setTimeout(() => { bar.style.width = w + '%'; }, 400);
    });

    // ─── CARD TILT ───
    const tiltCards = document.querySelectorAll('.stat-card, .qa-card, .af-card, .insight-card');
    tiltCards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;
            card.style.transform = `perspective(600px) rotateX(${y * -4}deg) rotateY(${x * 4}deg) translateY(-3px)`;
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });

    // ─── SMOOTH PAGE TRANSITIONS ───
    document.body.style.opacity = '0';
    requestAnimationFrame(() => {
        document.body.style.transition = 'opacity .3s ease';
        document.body.style.opacity = '1';
    });

    const navLinks = document.querySelectorAll('a[href^="/"]');
    navLinks.forEach(link => {
        link.addEventListener('click', e => {
            const href = link.getAttribute('href');
            if (!href || href.startsWith('//') || link.hasAttribute('download')) return;
            // Skip if report generation button
            if (link.closest('.actions-row') && link.getAttribute('onclick')) return;
            e.preventDefault();
            document.body.style.opacity = '0';
            setTimeout(() => { window.location.href = href; }, 250);
        });
    });

    // ─── NAVBAR SCROLL SHADOW ───
    const topnav = document.getElementById('topnav');
    if (topnav) {
        window.addEventListener('scroll', () => {
            topnav.style.boxShadow = window.scrollY > 8
                ? '0 2px 16px rgba(0,0,0,.06)'
                : 'none';
        }, { passive: true });
    }

    // ─── CLEAR HISTORY ───
    const clearBtn = document.getElementById('clearHistoryBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            if (!confirm('Clear all scan history?')) return;
            try {
                const res = await fetch('/clear-history', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    alert('History cleared.');
                    location.reload();
                }
            } catch (err) {
                alert('Failed to clear history.');
            }
        });
    }
});

/* ─── COUNTER ANIMATION ─── */
function animateCounter(el, start, end, duration) {
    const t0 = performance.now();
    function tick(now) {
        const p = Math.min((now - t0) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(start + (end - start) * eased);
        if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

/* ─── GENERATE REPORT ─── */
async function generateReport(type) {
    const dataEl = document.getElementById('resultData');
    if (!dataEl) return alert('No result data found.');

    const data = JSON.parse(dataEl.textContent);
    let payload;

    if (type === 'url') {
        const urlEl = document.getElementById('resultUrl');
        payload = { type: 'url', url: urlEl ? urlEl.textContent : '', data: data };
    } else {
        const msgEl = document.getElementById('resultMessage');
        payload = { type: 'mail', message: msgEl ? msgEl.textContent : '', data: data };
    }

    const btn = event.target.closest('.action-btn');
    const origHTML = btn.innerHTML;
    btn.innerHTML = '<span class="material-icons-round">hourglass_top</span> Generating...';
    btn.disabled = true;

    try {
        const res = await fetch('/generate-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await res.json();

        if (result.download_url) {
            btn.innerHTML = '<span class="material-icons-round">check_circle</span> Done!';
            setTimeout(() => {
                window.location.href = result.download_url;
                btn.innerHTML = origHTML;
                btn.disabled = false;
            }, 800);
        } else {
            throw new Error(result.error || 'Unknown error');
        }
    } catch (err) {
        alert('Report generation failed: ' + err.message);
        btn.innerHTML = origHTML;
        btn.disabled = false;
    }
}