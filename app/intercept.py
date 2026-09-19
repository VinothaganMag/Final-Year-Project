"""Interception layer for the browser extension and Windows launcher.

Kept separate from the analyzer: this blueprint only validates an intercepted URL,
delegates to the existing ``predict_url`` model code, renders an interstitial,
and provides a focus restore endpoint for desktop applications.
"""

import sys
from urllib.parse import urlparse

from flask import Blueprint, jsonify, render_template, request

from .model import predict_url

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = ("http", "https")

intercept_bp = Blueprint("intercept", __name__)


def validate_target(target: str) -> str:
    """Return an error message for an unusable target URL, or an empty string."""
    if not target:
        return "No URL was supplied for analysis."
    if len(target) > MAX_URL_LENGTH:
        return f"URL exceeds the {MAX_URL_LENGTH} character limit."
    parsed = urlparse(target)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return "Only http and https URLs can be analysed."
    if not parsed.netloc:
        return "URL is missing a hostname."
    return ""


@intercept_bp.route("/intercept")
def intercept():
    target = request.args.get("target", "").strip()
    source = request.args.get("source", "browser").strip()
    caller_hwnd = request.args.get("caller_hwnd", "0").strip()

    error = validate_target(target)
    if error:
        return (
            render_template(
                "intercept.html",
                url=target,
                data=None,
                error=error,
                source=source,
                caller_hwnd=caller_hwnd,
            ),
            400,
        )

    data = predict_url(target)

    from .app import add_activity

    add_activity("URL", target, data)

    return render_template(
        "intercept.html",
        url=target,
        data=data,
        error=None,
        source=source,
        caller_hwnd=caller_hwnd,
    )


@intercept_bp.route("/intercept/leave", methods=["POST"])
def leave():
    """Restore focus to the calling desktop window if a valid caller_hwnd was provided."""
    body = request.get_json(silent=True) or {}
    raw_hwnd = body.get("caller_hwnd", 0)

    try:
        hwnd = int(raw_hwnd)
    except (TypeError, ValueError):
        hwnd = 0

    focused = False
    if hwnd > 0 and sys.platform == "win32":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            if user32.IsWindow(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
                user32.SetForegroundWindow(hwnd)
                focused = True
        except Exception:
            pass

    return jsonify({"status": "ok", "focused": focused})


@intercept_bp.route("/intercept/health")
def health():
    return jsonify({"status": "ok"})
