# CRIS Link Guard (Phase 1)

Chromium (Chrome / Edge / Brave) Manifest V3 extension that intercepts **cross-site, top-frame
http/https navigations** on desktop and routes them through the local Flask analyzer before the
browser opens them.

## How it works

1. `background.js` listens to `chrome.webNavigation.onBeforeNavigate` (`frameId === 0`).
2. Navigations are skipped when: the scheme is not http/https, the host is the analyzer itself, the
   target is on the same registrable domain as the current page, an approval is pending for that exact
   URL, a redirect loop is detected, or the analyzer is unreachable (**fail open**).
3. Otherwise the tab is redirected to `http://127.0.0.1:5000/intercept?target=<encoded url>`, which
   renders the existing risk score, classification, reasons and feature breakdown.
4. **Continue** → the page posts a message, `bridge.js` forwards it to the service worker, the exact URL
   is added to a one-shot 60-second allowlist, and only after the acknowledgement does the page
   `location.replace()` to the original URL.
5. **Leave** → goes back in history.

No blocking is performed: the interstitial is advisory, and every navigation ultimately remains the
user's choice.

## Install (development)

1. Start the analyzer first:
   ```bash
   cd app && python app.py     # http://127.0.0.1:5000
   ```
2. Open `chrome://extensions`, enable **Developer mode**.
3. **Load unpacked** → select this `extension/` directory.
4. Click any external link. The interstitial should appear before the site loads.

The toolbar badge shows `off` when the analyzer cannot be reached; links then navigate normally.

## Configuration

`chrome://extensions` → CRIS Link Guard → **Extension options** lets you change the analyzer origin.
Any change also requires editing `host_permissions` and the content-script `matches` pattern in
`manifest.json`, because Chrome grants those at install time.

## Known limitations

- Same-site navigation is intentionally never intercepted.
- `POST` form submissions cannot be replayed, so any intercepted navigation is re-issued as a `GET`;
  same-site submissions (the common case) are unaffected because they are not intercepted.
- Incognito windows require explicitly allowing the extension there.
- Every intercepted URL is sent to the local analyzer and appended to its in-memory activity log.
