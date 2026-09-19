"""Interception layer for the browser extension.

Kept separate from the analyzer: this blueprint only validates an intercepted URL,
delegates to the existing ``predict_url`` model code, and renders an interstitial.
"""

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

    error = validate_target(target)
    if error:
        return render_template("intercept.html", url=target, data=None, error=error), 400

    data = predict_url(target)

    from .app import add_activity

    add_activity("URL", target, data)

    return render_template("intercept.html", url=target, data=data, error=None)


@intercept_bp.route("/intercept/health")
def health():
    return jsonify({"status": "ok"})
