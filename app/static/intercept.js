/* ════════════════════════════════════════════════
   INTERSTITIAL DECISION HANDLER
   Talks to the browser extension's content-script bridge
   (window.postMessage) so the original URL is allowlisted
   exactly once before navigation continues.
   ════════════════════════════════════════════════ */

(function () {
    const ACK_TIMEOUT_MS = 1500;

    document.addEventListener('DOMContentLoaded', () => {
        const continueBtn = document.getElementById('continueBtn');
        const leaveBtn = document.getElementById('leaveBtn');
        const note = document.getElementById('interceptNote');

        // ─────────────────────────────────────────
        // LEAVE BUTTON
        // ─────────────────────────────────────────
        if (leaveBtn) {
            leaveBtn.addEventListener('click', () => {
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.location.assign('/');
                }
            });
        }

        if (!continueBtn) return;

        const target = continueBtn.dataset.target;

        // ─────────────────────────────────────────
        // CONTINUE BUTTON
        // ─────────────────────────────────────────
        continueBtn.addEventListener('click', () => {
            continueBtn.disabled = true;

            if (note) {
                note.textContent = 'Approving this link…';
            }

            let done = false;

            // Navigate to the original URL
            const go = () => {
                if (done) return;

                done = true;

                window.removeEventListener('message', onMessage);

                window.location.replace(target);
            };

            // ─────────────────────────────────────
            // LISTEN FOR EXTENSION ACK
            // ─────────────────────────────────────
            function onMessage(event) {
                if (
                    event.source !== window ||
                    event.origin !== window.location.origin
                ) {
                    return;
                }

                const msg = event.data;

                if (
                    !msg ||
                    msg.source !== 'cris-bridge' ||
                    msg.type !== 'CRIS_CONTINUE_ACK'
                ) {
                    return;
                }

                // Make sure ACK belongs to this exact URL
                if (msg.url !== target) return;

                go();
            }

            window.addEventListener('message', onMessage);

            // ─────────────────────────────────────
            // SEND APPROVAL TO EXTENSION
            // ─────────────────────────────────────
            window.postMessage(
                {
                    source: 'cris-page',
                    type: 'CRIS_CONTINUE',
                    url: target
                },
                window.location.origin
            );

            // ─────────────────────────────────────
            // FALLBACK
            // If extension does not respond,
            // continue after 1.5 seconds.
            // ─────────────────────────────────────
            setTimeout(go, ACK_TIMEOUT_MS);
        });
    });
})();