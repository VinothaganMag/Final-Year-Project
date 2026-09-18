/* ════════════════════════════════════════════════
   CRIS LINK GUARD — SERVICE WORKER
   Intercepts cross-site top-frame http(s) navigations and
   redirects them to the local analyzer's interstitial page.
   Fails open whenever the analyzer is unreachable.
   ════════════════════════════════════════════════ */

const DEFAULT_ANALYZER = 'http://127.0.0.1:5000';

const APPROVAL_TTL_MS = 60000;
const HEALTH_TTL_MS = 30000;
const LOOP_WINDOW_MS = 15000;
const LOOP_LIMIT = 2;

const SKIPPED_SCHEMES = ['chrome:', 'chrome-extension:', 'about:', 'file:', 'data:', 'blob:', 'view-source:', 'devtools:'];
const SKIPPED_HOSTS = ['chromewebstore.google.com', 'chrome.google.com'];

/** url -> expiry timestamp. One-shot: the entry is deleted when it is consumed. */
const approved = new Map();
/** tabId -> last committed top-frame URL, used for the cross-site comparison. */
const lastCommitted = new Map();
/** `tabId|url` -> {count, first} loop guard. */
const redirects = new Map();

let analyzerOrigin = DEFAULT_ANALYZER;
let health = { ok: false, checkedAt: 0 };

// ─────────────────────────────────────────────
// SETUP
// ─────────────────────────────────────────────

async function loadSettings() {
    const stored = await chrome.storage.local.get('analyzerOrigin');
    if (stored.analyzerOrigin) analyzerOrigin = stored.analyzerOrigin;
}

async function restoreApprovals() {
    const stored = await chrome.storage.session.get('approved');
    const entries = stored.approved || [];
    const now = Date.now();
    entries.forEach(([url, expiry]) => {
        if (expiry > now) approved.set(url, expiry);
    });
}

const ready = Promise.all([loadSettings(), restoreApprovals()]).catch(() => {});

chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && changes.analyzerOrigin) {
        analyzerOrigin = changes.analyzerOrigin.newValue || DEFAULT_ANALYZER;
        health = { ok: false, checkedAt: 0 };
    }
});

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

function persistApprovals() {
    chrome.storage.session.set({ approved: [...approved.entries()] }).catch(() => {});
}

function approve(url) {
    const now = Date.now();
    for (const [key, expiry] of approved) {
        if (expiry <= now) approved.delete(key);
    }
    approved.set(url, now + APPROVAL_TTL_MS);
    persistApprovals();
}

/** Consume an approval. Returns true only for an exact, unexpired, unused match. */
function consumeApproval(url) {
    const expiry = approved.get(url);
    if (!expiry) return false;
    approved.delete(url);
    persistApprovals();
    if (expiry <= Date.now()) return false;
    return true;
}

const MULTI_PART_SUFFIXES = new Set(['co', 'com', 'net', 'org', 'ac', 'gov', 'edu']);

/** Best-effort registrable domain (no public suffix list bundled on purpose). */
function registrableDomain(hostname) {
    const labels = hostname.toLowerCase().split('.').filter(Boolean);
    if (labels.length <= 2) return labels.join('.');
    const [tld, sld] = [labels[labels.length - 1], labels[labels.length - 2]];
    if (tld.length === 2 && MULTI_PART_SUFFIXES.has(sld)) return labels.slice(-3).join('.');
    return labels.slice(-2).join('.');
}

function isCrossSite(targetUrl, currentUrl) {
    if (!currentUrl) return true;
    try {
        const a = registrableDomain(new URL(targetUrl).hostname);
        const b = registrableDomain(new URL(currentUrl).hostname);
        return Boolean(a) && a !== b;
    } catch (err) {
        return true;
    }
}

function isSkipped(url) {
    let parsed;
    try {
        parsed = new URL(url);
    } catch (err) {
        return true;
    }
    if (SKIPPED_SCHEMES.includes(parsed.protocol)) return true;
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return true;
    if (SKIPPED_HOSTS.includes(parsed.hostname)) return true;
    if (url.startsWith(analyzerOrigin)) return true;
    return false;
}

/** Guards against an interstitial <-> target ping-pong if approval ever fails. */
function loopTripped(tabId, url) {
    const key = `${tabId}|${url}`;
    const now = Date.now();
    const entry = redirects.get(key);
    if (!entry || now - entry.first > LOOP_WINDOW_MS) {
        redirects.set(key, { count: 1, first: now });
        return false;
    }
    entry.count += 1;
    return entry.count > LOOP_LIMIT;
}

async function analyzerIsUp() {
    const now = Date.now();
    if (now - health.checkedAt < HEALTH_TTL_MS) return health.ok;
    try {
        const res = await fetch(`${analyzerOrigin}/intercept/health`, { cache: 'no-store' });
        health = { ok: res.ok, checkedAt: now };
    } catch (err) {
        health = { ok: false, checkedAt: now };
    }
    setBadge(health.ok);
    return health.ok;
}

function setBadge(ok) {
    chrome.action.setBadgeText({ text: ok ? '' : 'off' }).catch(() => {});
    chrome.action.setBadgeBackgroundColor({ color: '#dc2626' }).catch(() => {});
    chrome.action
        .setTitle({ title: ok ? 'CRIS Link Guard — active' : 'CRIS Link Guard — analyzer unreachable (links pass through)' })
        .catch(() => {});
}

function interstitialUrl(target) {
    return `${analyzerOrigin}/intercept?target=${encodeURIComponent(target)}`;
}

// ─────────────────────────────────────────────
// INTERCEPTION
// ─────────────────────────────────────────────

chrome.webNavigation.onCommitted.addListener((details) => {
    if (details.frameId !== 0) return;
    lastCommitted.set(details.tabId, details.url);
});

chrome.tabs.onRemoved.addListener((tabId) => {
    lastCommitted.delete(tabId);
    for (const key of redirects.keys()) {
        if (key.startsWith(`${tabId}|`)) redirects.delete(key);
    }
});

chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
    if (details.frameId !== 0) return;

    await ready;

    const target = details.url;
    if (isSkipped(target)) return;
    if (consumeApproval(target)) return;
    if (!isCrossSite(target, lastCommitted.get(details.tabId))) return;
    if (loopTripped(details.tabId, target)) return;
    if (!(await analyzerIsUp())) return;

    try {
        await chrome.tabs.update(details.tabId, { url: interstitialUrl(target) });
    } catch (err) {
        // Tab closed or navigation already committed: let the browser carry on.
    }
});

// ─────────────────────────────────────────────
// APPROVAL CHANNEL (from bridge.js on the interstitial)
// ─────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || message.type !== 'CRIS_CONTINUE') return false;
    if (!sender.url || !sender.url.startsWith(`${analyzerOrigin}/intercept`)) {
        sendResponse({ ok: false });
        return false;
    }
    if (typeof message.url !== 'string' || !message.url) {
        sendResponse({ ok: false });
        return false;
    }
    approve(message.url);
    sendResponse({ ok: true, url: message.url });
    return false;
});

chrome.runtime.onInstalled.addListener(() => {
    analyzerIsUp();
});
chrome.runtime.onStartup.addListener(() => {
    analyzerIsUp();
});
