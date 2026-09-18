import json
import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory, session
from model import SUSPICIOUS_KEYWORDS, predict_mail, predict_url
from report_generator import REPORTS_DIR, generate_mail_report, generate_url_report

app = Flask(__name__)
app.secret_key = "cyberrisk_intel_2026_secret"

# ═══════════════════════════════════════════════
# ACTIVITY VAULT (in-memory, session-based)
# ═══════════════════════════════════════════════

ACTIVITY_LOG = []
MAX_HISTORY = 50


def add_activity(scan_type: str, input_text: str, result: dict):
    entry = {
        "id": len(ACTIVITY_LOG) + 1,
        "type": scan_type,
        "input": input_text[:120],
        "status": result.get("status", result.get("prediction", "—")),
        "score": result.get("risk_score", result.get("spam_probability", "—")),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    ACTIVITY_LOG.insert(0, entry)
    if len(ACTIVITY_LOG) > MAX_HISTORY:
        ACTIVITY_LOG.pop()


# ═══════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════


@app.route("/")
def control_center():
    stats = {
        "total_scans": len(ACTIVITY_LOG),
        "url_scans": sum(1 for a in ACTIVITY_LOG if a["type"] == "URL"),
        "mail_scans": sum(1 for a in ACTIVITY_LOG if a["type"] == "Email"),
        "threats_found": sum(
            1 for a in ACTIVITY_LOG if a["status"] in ["Dangerous", "Spam / Phishing"]
        ),
        "recent": ACTIVITY_LOG[:5],
    }
    return render_template("control_center.html", stats=stats)


@app.route("/url")
def url_inspector():
    return render_template("url_inspector.html")


@app.route("/url/result")
def url_result():
    url = request.args.get("url", "")
    if not url:
        return render_template("url_inspector.html", error="Please enter a URL.")
    data = predict_url(url)
    add_activity("URL", url, data)
    return render_template("url_result.html", url=url, data=data)


@app.route("/mail")
def mail_analyzer():
    return render_template("mail_analyzer.html")


@app.route("/mail/result")
def mail_result():
    msg = request.args.get("message", "")
    if not msg:
        return render_template("mail_analyzer.html", error="Please enter a message.")
    data = predict_mail(msg)
    add_activity("Email", msg, data)
    return render_template("mail_result.html", message=msg, data=data)


@app.route("/insights")
def insights():
    kw_freq = {}
    for entry in ACTIVITY_LOG:
        if entry["type"] == "URL":
            inp = entry["input"].lower()
            for kw in SUSPICIOUS_KEYWORDS:
                if kw in inp:
                    kw_freq[kw] = kw_freq.get(kw, 0) + 1

    risk_dist = {"Safe": 0, "Suspicious": 0, "Dangerous": 0}
    for entry in ACTIVITY_LOG:
        status = entry.get("status", "")
        if status in risk_dist:
            risk_dist[status] += 1

    mail_dist = {"Legitimate": 0, "Spam / Phishing": 0}
    for entry in ACTIVITY_LOG:
        status = entry.get("status", "")
        if status in mail_dist:
            mail_dist[status] += 1

    return render_template(
        "insights.html",
        kw_freq=kw_freq,
        risk_dist=risk_dist,
        mail_dist=mail_dist,
        total=len(ACTIVITY_LOG),
    )


@app.route("/reports")
def reports():
    report_files = []
    if os.path.exists(REPORTS_DIR):
        for f in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if f.endswith(".pdf"):
                stat = os.stat(os.path.join(REPORTS_DIR, f))
                report_files.append(
                    {
                        "name": f,
                        "size": f"{stat.st_size / 1024:.1f} KB",
                        "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    }
                )
    return render_template("reports.html", reports=report_files)


@app.route("/history")
def history():
    return render_template("history.html", activities=ACTIVITY_LOG)


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/about")
def about():
    return render_template("about.html")


# ═══════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════


@app.route("/predict-url", methods=["POST"])
def api_predict_url():
    body = request.get_json(force=True)
    url = body.get("url", "")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    data = predict_url(url)
    add_activity("URL", url, data)
    return jsonify(data)


@app.route("/predict-mail", methods=["POST"])
def api_predict_mail():
    body = request.get_json(force=True)
    msg = body.get("message", "")
    if not msg:
        return jsonify({"error": "No message provided"}), 400
    data = predict_mail(msg)
    add_activity("Email", msg, data)
    return jsonify(data)


@app.route("/generate-report", methods=["POST"])
def api_generate_report():
    body = request.get_json(force=True)
    rtype = body.get("type", "url")

    if rtype == "url":
        url = body.get("url", "")
        data = body.get("data", {})
        if not url or not data:
            return jsonify({"error": "Missing url or data"}), 400
        filename = generate_url_report(url, data)
    elif rtype == "mail":
        message = body.get("message", "")
        data = body.get("data", {})
        if not message or not data:
            return jsonify({"error": "Missing message or data"}), 400
        filename = generate_mail_report(message, data)
    else:
        return jsonify({"error": "Invalid report type"}), 400

    return jsonify({"filename": filename, "download_url": f"/download-report/{filename}"})


@app.route("/download-report/<filename>")
def download_report(filename):
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)


@app.route("/clear-history", methods=["POST"])
def clear_history():
    ACTIVITY_LOG.clear()
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
