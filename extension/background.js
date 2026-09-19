/* ════════════════════════════════════════════════
   CRIS LINK GUARD — SERVICE WORKER
   Intercepts user-clicked cross-site top-frame http(s) navigations
   and redirects them to the local analyzer's interstitial page.
   Fails open whenever the analyzer is unreachable.
   ════════════════════════════════════════════════ */

const DEFAULT_ANALYZER = 'http://127.0.0.1:5000';

const APPROVAL_TTL_MS = 60000;
const HEALTH_TTL_MS = 30000;
const LOOP_WINDOW_MS = 15000;
const LOOP_LIMIT = 2;
const INTENT_TTL_MS = 3000;

const SKIPPED_SCHEMES = ['chrome:', 'chrome-extension:', 'about:', 'file:', 'data:', 'blob:', 'view-source:', 'devtools:'];
const SKIPPED_HOSTS = ['chromewebstore.google.com', 'chrome.google.com'];

/** url -> expiry timestamp. One-shot: the entry is deleted when it is consumed. */
const approved = new Map();
/** tabId -> expiry timestamp for approved navigation chains (redirects). */
const approvedChains = new Map();
/** tabId -> last committed top-frame URL, used for the cross-site comparison. */
const lastCommitted = new Map();
/** `tabId|url` -> {count, first} loop guard. */
const redirects = new Map();

/** User intent tracking maps */
const sameTabIntents = new Map(); // tabId -> { targetUrl, originalUrl, timestamp }
const newTabIntents = new Map();  // targetUrl -> { originalUrl, timestamp }

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

async function initExistingTabs() {
    try {
        const tabs = await chrome.tabs.query({});
        for (const tab of tabs) {
            if (tab.id && tab.url && !isSkipped(tab.url)) {
                lastCommitted.set(tab.id, tab.url);
            }
        }
    } catch (err) {}
}

const ready = Promise.all([loadSettings(), restoreApprovals(), initExistingTabs()]).catch(() => {});

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

function approve(url, tabId) {
    if (!url || typeof url !== 'string') return;
    const now = Date.now();
    for (const [key, expiry] of approved) {
        if (expiry <= now) approved.delete(key);
    }
    approved.set(url, now + APPROVAL_TTL_MS);
    if (tabId) {
        approvedChains.set(tabId, now + APPROVAL_TTL_MS);
    }
    persistApprovals();
}

/** Consume an approval or active redirect chain. */
function consumeApproval(url, tabId) {
    const now = Date.now();
    const expiry = approved.get(url);
    if (expiry) {
        approved.delete(url);
        persistApprovals();
        if (expiry > now) {
            if (tabId) approvedChains.set(tabId, now + APPROVAL_TTL_MS);
            return true;
        }
    }

    if (tabId && approvedChains.has(tabId)) {
        const chainExpiry = approvedChains.get(tabId);
        if (chainExpiry > now) {
            return true;
        } else {
            approvedChains.delete(tabId);
        }
    }

    return false;
}

const MULTI_PART_SUFFIXES = new Set(['co', 'com', 'net', 'org', 'ac', 'gov', 'edu']);

/** Best-effort registrable domain (no public suffix list bundled on purpose). */
function registrableDomain(hostname) {
    if (!hostname) return '';
    const labels = hostname.toLowerCase().split('.').filter(Boolean);
    if (labels.length <= 2) return labels.join('.');
    const [tld, sld] = [labels[labels.length - 1], labels[labels.length - 2]];
    if (tld.length === 2 && MULTI_PART_SUFFIXES.has(sld)) return labels.slice(-3).join('.');
    return labels.slice(-2).join('.');
}

function isCrossSite(targetUrl, currentUrl) {
    if (!currentUrl) return false;
    try {
        const a = registrableDomain(new URL(targetUrl).hostname);
        const b = registrableDomain(new URL(currentUrl).hostname);
        return Boolean(a) && a !== b;
    } catch (err) {
        return false;
    }
}

function extractWrappedUrl(rawUrl) {
    if (!rawUrl || typeof rawUrl !== 'string') return null;
    try {
        const parsed = new URL(rawUrl);
        if (!parsed.search) return null;
        const params = new URLSearchParams(parsed.search);
        const keysToTry = ['q', 'url', 'target', 'dest', 'destination', 'link', 'redirect', 'to', 'u', 'r'];

        for (const key of keysToTry) {
            const val = params.get(key);
            if (val) {
                try {
                    const u = new URL(val);
                    if (u.protocol === 'http:' || u.protocol === 'https:') {
                        return u.href;
                    }
                } catch (e) {}
            }
        }

        for (const [_, val] of params.entries()) {
            if (val && (val.startsWith('http://') || val.startsWith('https://'))) {
                try {
                    const u = new URL(val);
                    return u.href;
                } catch (e) {}
            }
        }
    } catch (err) {}
    return null;
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
// USER CLICK INTENT TRACKING
// ─────────────────────────────────────────────

function cleanupStaleIntents() {
    const now = Date.now();
    for (const [tabId, entry] of sameTabIntents.entries()) {
        if (now - entry.timestamp > INTENT_TTL_MS) sameTabIntents.delete(tabId);
    }
    for (const [targetUrl, entry] of newTabIntents.entries()) {
        if (now - entry.timestamp > INTENT_TTL_MS) newTabIntents.delete(targetUrl);
    }
    for (const [tabId, expiry] of approvedChains.entries()) {
        if (now > expiry) approvedChains.delete(tabId);
    }
}

setInterval(cleanupStaleIntents, 5000);

function matchesIntent(storedTarget, storedOriginal, navTarget) {
    if (!navTarget || typeof navTarget !== 'string') return false;
    if (storedTarget === navTarget || storedOriginal === navTarget) return true;

    const extracted = extractWrappedUrl(navTarget);
    if (extracted && (extracted === storedTarget || extracted === storedOriginal)) return true;

    try {
        const navDom = registrableDomain(new URL(navTarget).hostname);
        const storedDom = registrableDomain(new URL(storedTarget).hostname);
        if (navDom && storedDom && navDom === storedDom) return true;
    } catch (err) {}

    return false;
}

function consumeUserClickIntent(tabId, targetUrl) {
    cleanupStaleIntents();
    const now = Date.now();

    // 1. Check Same-Tab intent
    const sameEntry = sameTabIntents.get(tabId);
    if (sameEntry && now - sameEntry.timestamp <= INTENT_TTL_MS) {
        if (matchesIntent(sameEntry.targetUrl, sameEntry.originalUrl, targetUrl)) {
            sameTabIntents.delete(tabId);
            return true;
        }
    }

    // 2. Check New-Tab intent
    for (const [urlKey, entry] of newTabIntents.entries()) {
        if (now - entry.timestamp <= INTENT_TTL_MS) {
            if (matchesIntent(urlKey, entry.originalUrl, targetUrl)) {
                newTabIntents.delete(urlKey);
                return true;
            }
        }
    }

    return false;
}

// ─────────────────────────────────────────────
// INTERCEPTION & NAVIGATION LISTENERS
// ─────────────────────────────────────────────

chrome.webNavigation.onCommitted.addListener((details) => {
    if (details.frameId !== 0) return;
    lastCommitted.set(details.tabId, details.url);
    if (approvedChains.has(details.tabId)) {
        setTimeout(() => approvedChains.delete(details.tabId), 2000);
    }
});

chrome.tabs.onRemoved.addListener((tabId) => {
    lastCommitted.delete(tabId);
    sameTabIntents.delete(tabId);
    approvedChains.delete(tabId);
    for (const key of redirects.keys()) {
        if (key.startsWith(`${tabId}|`)) redirects.delete(key);
    }
});

chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
    if (details.frameId !== 0) return;

    await ready;

    const target = details.url;

    if (isSkipped(target)) return;
    if (consumeApproval(target, details.tabId)) return;
    if (loopTripped(details.tabId, target)) return;

    // Verify user click intent
    if (!consumeUserClickIntent(details.tabId, target)) return;

    // If current committed URL is known, verify cross-site status
    const currentUrl = lastCommitted.get(details.tabId);
    if (currentUrl && !isCrossSite(target, currentUrl)) return;

    if (!(await analyzerIsUp())) return;

    try {
        // Intercept destination URL (use extracted wrapped target if present)
        const effectiveTarget = extractWrappedUrl(target) || target;
        await chrome.tabs.update(details.tabId, { url: interstitialUrl(effectiveTarget) });
    } catch (err) {
        // Tab closed or navigation already committed: let the browser carry on.
    }
});

// ─────────────────────────────────────────────
// MESSAGING & APPROVAL CHANNEL
// ─────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || typeof message !== 'object') return false;

    // User click intent signal from click_tracker.js
    if (message.type === 'CRIS_USER_CLICK' && typeof message.targetUrl === 'string') {
        const timestamp = Date.now();
        const originalUrl = typeof message.originalUrl === 'string' ? message.originalUrl : message.targetUrl;
        if (message.isNewTab) {
            newTabIntents.set(message.targetUrl, { originalUrl, timestamp });
        } else if (sender.tab && sender.tab.id) {
            sameTabIntents.set(sender.tab.id, { targetUrl: message.targetUrl, originalUrl, timestamp });
        }
        return false;
    }

    // Continue approval message from bridge.js
    if (message.type === 'CRIS_CONTINUE') {
        if (!sender.url || !sender.url.startsWith(`${analyzerOrigin}/intercept`)) {
            sendResponse({ ok: false });
            return false;
        }
        if (typeof message.url !== 'string' || !message.url) {
            sendResponse({ ok: false });
            return false;
        }
        approve(message.url, sender.tab?.id);
        sendResponse({ ok: true, url: message.url });
        return false;
    }

    return false;
});

chrome.runtime.onInstalled.addListener(() => {
    analyzerIsUp();
});
chrome.runtime.onStartup.addListener(() => {
    analyzerIsUp();
});
