"""CRIS Windows URL Interception Launcher.

Captures HTTP/HTTPS URLs launched from external Windows desktop applications,
records the calling application's active window handle (HWND), constructs the
CRIS Flask intercept URL, and opens it in the user's browser.
"""

import json
import os
import subprocess
import sys
import urllib.parse

DEFAULT_FLASK_ORIGIN = "http://127.0.0.1:5000"
CONFIG_FILE_NAME = "cris_config.json"


def get_config_path() -> str:
    """Return absolute path to the local cris_config.json file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE_NAME)


def get_foreground_hwnd() -> int:
    """Return HWND handle of active foreground window on Windows, or 0 if non-Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            return int(hwnd) if hwnd else 0
        except Exception:
            return 0
    return 0


def build_intercept_url(
    target_url: str,
    flask_origin: str = DEFAULT_FLASK_ORIGIN,
    caller_hwnd: int = 0,
) -> str:
    """Validate target URL and build the CRIS Flask intercept URL with source=desktop and optional caller_hwnd."""
    if not target_url or not isinstance(target_url, str):
        raise ValueError("Target URL must be a non-empty string.")

    cleaned = target_url.strip()
    if not cleaned:
        raise ValueError("Target URL cannot be empty or whitespace.")

    parsed = urllib.parse.urlparse(cleaned)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.")

    if not parsed.netloc:
        raise ValueError("Target URL is missing a valid hostname/netloc.")

    encoded = urllib.parse.quote(cleaned, safe="")
    origin = flask_origin.rstrip("/")
    base_url = f"{origin}/intercept?target={encoded}&source=desktop"
    if caller_hwnd and caller_hwnd > 0:
        base_url += f"&caller_hwnd={caller_hwnd}"
    return base_url


def find_real_browser() -> list[str]:
    """Locate the downstream real web browser executable to avoid launcher loop recursion."""
    # 1. Check local config file if saved by registration script
    cfg_path = get_config_path()
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                browser_path = cfg.get("real_browser_path")
                if browser_path and os.path.isfile(browser_path):
                    return [browser_path]
        except Exception:
            pass

    # 2. Check well-known Windows browser paths
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    for exe in candidates:
        if exe and os.path.isfile(exe):
            return [exe]

    # 3. Fallback to Windows default shell command launcher if no direct binary matched
    comspec = os.environ.get("COMSPEC", "cmd.exe")
    return [comspec, "/c", "start", ""]


def launch_url(
    target_url: str,
    flask_origin: str = DEFAULT_FLASK_ORIGIN,
    caller_hwnd: int | None = None,
) -> str:
    """Build intercept URL and launch it in the downstream browser process."""
    if caller_hwnd is None:
        caller_hwnd = get_foreground_hwnd()

    intercept_url = build_intercept_url(target_url, flask_origin, caller_hwnd=caller_hwnd)
    browser_cmd = find_real_browser()

    if browser_cmd[-1] == "":
        cmd = browser_cmd[:-1] + [intercept_url]
    else:
        cmd = browser_cmd + [intercept_url]

    subprocess.Popen(cmd)
    return intercept_url


def main():
    if len(sys.argv) < 2:
        print("CRIS Launcher - Windows System-Level URL Interceptor Prototype")
        print("Usage: python cris_launcher.py <URL>")
        sys.exit(1)

    # Capture the foreground window handle BEFORE spawning browser process
    hwnd = get_foreground_hwnd()
    raw_url = sys.argv[1]
    try:
        url = launch_url(raw_url, caller_hwnd=hwnd)
        print(f"[CRIS Launcher] Routed '{raw_url}' -> '{url}'")
    except Exception as err:
        print(f"[CRIS Launcher] Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
