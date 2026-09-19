/* ════════════════════════════════════════════════
   CRIS LINK GUARD — CONTENT SCRIPT CLICK TRACKER
   Listens for physical user click events on external links,
   extracts wrapped redirect proxy targets (e.g. google.com/url?q=...),
   and relays click intent signals to background.js.
   ════════════════════════════════════════════════ */

(function () {
    const MULTI_PART_SUFFIXES = new Set(['co', 'com', 'net', 'org', 'ac', 'gov', 'edu']);

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

    function handleUserClick(event) {
        // Physical click or auxclick (middle click)
        if (!event || (!event.isTrusted && event.isTrusted !== undefined)) return;

        const targetEl = event.target;
        if (!targetEl || typeof targetEl.closest !== 'function') return;

        const link = targetEl.closest('a[href], area[href], [data-href], [data-url]');
        if (!link) return;

        let href = link.href || link.getAttribute('data-href') || link.getAttribute('data-url');
        if (!href) return;

        try {
            href = new URL(href, window.location.href).href;
        } catch (err) {
            return;
        }

        let parsed;
        try {
            parsed = new URL(href);
        } catch (err) {
            return;
        }

        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return;

        // Check if link is wrapped by a redirect proxy (e.g. google.com/url?q=...)
        const wrappedTarget = extractWrappedUrl(href);
        const effectiveTarget = wrappedTarget || href;

        // Skip same-site navigation relative to effective target
        if (!isCrossSite(effectiveTarget, window.location.href)) return;

        const isNewTab =
            event.button === 1 ||
            event.ctrlKey ||
            event.metaKey ||
            (link.getAttribute && link.getAttribute('target') === '_blank') ||
            link.target === '_blank';

        try {
            chrome.runtime.sendMessage({
                type: 'CRIS_USER_CLICK',
                targetUrl: effectiveTarget,
                originalUrl: href,
                isNewTab: Boolean(isNewTab)
            });
        } catch (err) {
            // Extension context may be unloaded or inactive
        }
    }

    // Capture phase event listeners
    window.addEventListener('click', handleUserClick, { capture: true, passive: true });
    window.addEventListener('auxclick', handleUserClick, { capture: true, passive: true });

    // Listen for window.open messages from page context bridge
    window.addEventListener('message', (event) => {
        if (event.source !== window) return;
        const msg = event.data;
        if (!msg || msg.type !== 'CRIS_WINDOW_OPEN' || !msg.url) return;

        try {
            const rawUrl = new URL(msg.url, window.location.href).href;
            const wrappedTarget = extractWrappedUrl(rawUrl);
            const effectiveTarget = wrappedTarget || rawUrl;

            if (isCrossSite(effectiveTarget, window.location.href)) {
                chrome.runtime.sendMessage({
                    type: 'CRIS_USER_CLICK',
                    targetUrl: effectiveTarget,
                    originalUrl: rawUrl,
                    isNewTab: true
                });
            }
        } catch (err) {}
    });
})();
