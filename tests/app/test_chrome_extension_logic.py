import time
from urllib.parse import parse_qs, urlparse

import pytest

MULTI_PART_SUFFIXES = {"co", "com", "net", "org", "ac", "gov", "edu"}
SKIPPED_SCHEMES = [
    "chrome:",
    "chrome-extension:",
    "about:",
    "file:",
    "data:",
    "blob:",
    "view-source:",
    "devtools:",
]
SKIPPED_HOSTS = ["chromewebstore.google.com", "chrome.google.com"]
DEFAULT_ANALYZER = "http://127.0.0.1:5000"


def registrable_domain(hostname: str) -> str:
    if not hostname:
        return ""
    labels = [lbl for lbl in hostname.lower().split(".") if lbl]
    if len(labels) <= 2:
        return ".".join(labels)
    tld, sld = labels[-1], labels[-2]
    if len(tld) == 2 and sld in MULTI_PART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def is_cross_site(target_url: str, current_url: str) -> bool:
    if not current_url:
        return False
    try:
        a = registrable_domain(urlparse(target_url).hostname or "")
        b = registrable_domain(urlparse(current_url).hostname or "")
        return bool(a) and a != b
    except Exception:
        return False


def extract_wrapped_url(raw_url: str) -> str | None:
    if not raw_url or not isinstance(raw_url, str):
        return None
    try:
        parsed = urlparse(raw_url)
        if not parsed.query:
            return None
        params = parse_qs(parsed.query)
        keys_to_try = ["q", "url", "target", "dest", "destination", "link", "redirect", "to", "u", "r"]

        for key in keys_to_try:
            vals = params.get(key)
            if vals and vals[0]:
                try:
                    u = urlparse(vals[0])
                    if u.scheme in ("http", "https"):
                        return vals[0]
                except Exception:
                    pass

        for vals in params.values():
            for val in vals:
                if val.startswith("http://") or val.startswith("https://"):
                    try:
                        u = urlparse(val)
                        if u.scheme in ("http", "https"):
                            return val
                    except Exception:
                        pass
    except Exception:
        pass
    return None


def is_skipped(url: str, analyzer_origin: str = DEFAULT_ANALYZER) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return True
    scheme = f"{parsed.scheme}:" if parsed.scheme else ""
    if scheme in SKIPPED_SCHEMES:
        return True
    if parsed.scheme not in ("http", "https"):
        return True
    if parsed.hostname in SKIPPED_HOSTS:
        return True
    if url.startswith(analyzer_origin):
        return True
    return False


class ExtensionIntentTracker:
    def __init__(self, intent_ttl_ms: int = 3000):
        self.intent_ttl_ms = intent_ttl_ms
        self.same_tab_intents = {}
        self.new_tab_intents = {}
        self.approved = {}

    def approve(self, url: str, ttl_ms: int = 60000):
        self.approved[url] = time.time() * 1000 + ttl_ms

    def consume_approval(self, url: str) -> bool:
        expiry = self.approved.pop(url, None)
        if not expiry:
            return False
        return expiry > (time.time() * 1000)

    def record_click_intent(self, target_url: str, original_url: str | None = None, tab_id: int | None = None, is_new_tab: bool = False):
        now = time.time() * 1000
        orig = original_url or target_url
        if is_new_tab:
            self.new_tab_intents[target_url] = {"original_url": orig, "timestamp": now}
        elif tab_id is not None:
            self.same_tab_intents[tab_id] = {"target_url": target_url, "original_url": orig, "timestamp": now}

    def _matches_intent(self, stored_target: str, stored_orig: str, nav_target: str) -> bool:
        if stored_target == nav_target or stored_orig == nav_target:
            return True
        extracted = extract_wrapped_url(nav_target)
        if extracted and (extracted == stored_target or extracted == stored_orig):
            return True
        try:
            nav_dom = registrable_domain(urlparse(nav_target).hostname or "")
            stored_dom = registrable_domain(urlparse(stored_target).hostname or "")
            if nav_dom and stored_dom and nav_dom == stored_dom:
                return True
        except Exception:
            pass
        return False

    def consume_user_click_intent(self, tab_id: int, target_url: str) -> bool:
        now = time.time() * 1000
        # Purge stale
        self.same_tab_intents = {
            tid: entry
            for tid, entry in self.same_tab_intents.items()
            if now - entry["timestamp"] <= self.intent_ttl_ms
        }
        self.new_tab_intents = {
            url: entry
            for url, entry in self.new_tab_intents.items()
            if now - entry["timestamp"] <= self.intent_ttl_ms
        }

        # Check Same-Tab
        same_entry = self.same_tab_intents.get(tab_id)
        if same_entry and (now - same_entry["timestamp"] <= self.intent_ttl_ms):
            if self._matches_intent(same_entry["target_url"], same_entry["original_url"], target_url):
                del self.same_tab_intents[tab_id]
                return True

        # Check New-Tab
        for url_key, entry in list(self.new_tab_intents.items()):
            if now - entry["timestamp"] <= self.intent_ttl_ms:
                if self._matches_intent(url_key, entry["original_url"], target_url):
                    del self.new_tab_intents[url_key]
                    return True

        return False

    def should_intercept(self, tab_id: int, target_url: str, current_url: str | None = None) -> bool:
        if is_skipped(target_url):
            return False
        if self.consume_approval(target_url):
            return False

        # Intent verification first
        if not self.consume_user_click_intent(tab_id, target_url):
            return False

        # If current URL is known, verify cross-site status
        if current_url and not is_cross_site(target_url, current_url):
            return False

        return True


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# UNIT TESTS FOR ALL REQUIRED SCENARIOS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_chatgpt_internal_navigation_no_cris():
    # ChatGPT chat switching
    chat1 = "https://chatgpt.com/c/chat-uuid-1"
    chat2 = "https://chatgpt.com/c/chat-uuid-2"
    assert is_cross_site(chat2, chat1) is False
    tracker = ExtensionIntentTracker()
    # No click intent registered for cross-site
    assert tracker.should_intercept(1, chat2, chat1) is False


def test_youtube_internal_navigation_no_cris():
    yt1 = "https://www.youtube.com/watch?v=abc123"
    yt2 = "https://www.youtube.com/watch?v=xyz789"
    assert is_cross_site(yt2, yt1) is False
    tracker = ExtensionIntentTracker()
    assert tracker.should_intercept(1, yt2, yt1) is False


def test_whatsapp_gmail_external_same_tab_link_cris():
    tracker = ExtensionIntentTracker()
    current = "https://mail.google.com/mail/u/0/#inbox"
    external = "https://phishing-site.example.com/login"

    tracker.record_click_intent(external, tab_id=1, is_new_tab=False)
    assert tracker.should_intercept(1, external, current) is True


def test_whatsapp_external_new_tab_link_cris():
    tracker = ExtensionIntentTracker()
    external = "https://phishing-site.example.com/login"

    # User clicks target="_blank" link in WhatsApp Web
    tracker.record_click_intent(external, is_new_tab=True)
    # New tab opened (tab_id 105, current_url is None/uncommitted)
    assert tracker.should_intercept(105, external, current_url=None) is True


def test_gmail_google_redirect_wrapper_cris():
    tracker = ExtensionIntentTracker()
    current = "https://mail.google.com/mail/u/0/#inbox"
    phishing_dest = "https://phishing-site.example.com/login"
    gmail_wrapper = f"https://www.google.com/url?q={phishing_dest}&sa=D"

    # Click tracker extracts wrapped URL phishing_dest
    extracted = extract_wrapped_url(gmail_wrapper)
    assert extracted == phishing_dest
    assert is_cross_site(extracted, current) is True

    # Record intent for effective target and original wrapper
    tracker.record_click_intent(phishing_dest, original_url=gmail_wrapper, is_new_tab=True)

    # When Google redirect wrapper tab opens
    assert tracker.should_intercept(106, gmail_wrapper, current_url=None) is True


def test_address_bar_navigation_no_cris():
    tracker = ExtensionIntentTracker()
    current = "https://siteA.com"
    typed_url = "https://siteB.com"
    # Typed in omnibox -> no intent registered
    assert tracker.should_intercept(1, typed_url, current) is False


def test_bookmark_navigation_no_cris():
    tracker = ExtensionIntentTracker()
    current = "https://siteA.com"
    bookmark_url = "https://siteB.com"
    assert tracker.should_intercept(1, bookmark_url, current) is False


def test_stale_intent_no_cris():
    tracker = ExtensionIntentTracker(intent_ttl_ms=50)
    current = "https://siteA.com"
    external = "https://external-phishing.com"

    tracker.record_click_intent(external, tab_id=1, is_new_tab=False)
    time.sleep(0.08)  # Wait past 50ms TTL

    assert tracker.should_intercept(1, external, current) is False


def test_redirect_chain_handling():
    tracker = ExtensionIntentTracker()
    t_co = "https://t.co/shortlink"
    bit_ly = "https://bit.ly/midlink"

    tracker.record_click_intent(t_co, tab_id=1, is_new_tab=False)
    assert tracker.should_intercept(1, t_co, "https://x.com") is True

    # User approves t.co on interstitial
    tracker.approve(t_co)

    # Approved URL passes
    assert tracker.should_intercept(1, t_co, "https://x.com") is False


def test_startup_populates_tab_state():
    tracker = ExtensionIntentTracker()
    # Simulate pre-existing tabs initialized at startup
    last_committed = {12: "https://mail.google.com/mail/u/0/#inbox"}

    target_external = "https://phishing-site.example.com/login"
    tracker.record_click_intent(target_external, tab_id=12, is_new_tab=False)

    # First click on pre-existing tab uses initialized last_committed URL
    assert tracker.should_intercept(12, target_external, current_url=last_committed[12]) is True
