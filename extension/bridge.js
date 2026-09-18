/* ════════════════════════════════════════════════
   CRIS LINK GUARD — CONTENT SCRIPT BRIDGE
   Relays the interstitial's Continue decision to the
   service worker, then acknowledges it back to the page.
   Injected only on the analyzer's /intercept page.
   ════════════════════════════════════════════════ */

window.addEventListener('message', (event) => {
    if (event.source !== window) return;
    if (event.origin !== window.location.origin) return;

    const msg = event.data;
    if (!msg || msg.source !== 'cris-page' || msg.type !== 'CRIS_CONTINUE') return;
    if (typeof msg.url !== 'string' || !msg.url) return;

    chrome.runtime.sendMessage({ type: 'CRIS_CONTINUE', url: msg.url }, (response) => {
        if (chrome.runtime.lastError || !response || !response.ok) return;
        window.postMessage(
            { source: 'cris-bridge', type: 'CRIS_CONTINUE_ACK', url: msg.url },
            window.location.origin
        );
    });
});
