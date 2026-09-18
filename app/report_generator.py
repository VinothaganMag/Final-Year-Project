import os
from datetime import datetime

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "static", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _get_status_color(status: str):
    if status == "Safe":
        return colors.HexColor("#16a34a")
    elif status == "Suspicious":
        return colors.HexColor("#eab308")
    return colors.HexColor("#dc2626")


def generate_url_report(url: str, data: dict) -> str:
    """Generate a PDF report for URL analysis. Returns the filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"url_report_{timestamp}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=30 * mm,
        rightMargin=30 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=22,
            spaceAfter=6,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=20,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionHead",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=18,
            spaceAfter=8,
            textColor=colors.HexColor("#2563eb"),
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyText2",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=4,
            textColor=colors.HexColor("#1e293b"),
            leading=14,
        )
    )

    elements = []

    # Title
    elements.append(Paragraph("🛡️ Cyber Risk Intelligence Report", styles["ReportTitle"]))
    elements.append(
        Paragraph(
            f'Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}',
            styles["ReportSubtitle"],
        )
    )
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    elements.append(Spacer(1, 12))

    # Analysis Type
    elements.append(Paragraph("Analysis Type: URL Inspection", styles["SectionHead"]))
    elements.append(Paragraph(f"<b>URL Analyzed:</b> {url}", styles["BodyText2"]))
    elements.append(Spacer(1, 8))

    # Risk Score & Status
    status_color = _get_status_color(data["status"])
    elements.append(Paragraph("Risk Assessment", styles["SectionHead"]))

    score_data = [
        ["Risk Score", "Status", "ML Prediction", "ML Confidence"],
        [
            str(data["risk_score"]) + "/100",
            data["status"],
            data["ml_prediction"],
            str(data["ml_confidence"]) + "%",
        ],
    ]
    score_table = Table(score_data, colWidths=[100, 100, 100, 100])
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f9fafb")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(score_table)
    elements.append(Spacer(1, 12))

    # Reasons
    elements.append(Paragraph("Findings & Explanations", styles["SectionHead"]))
    for i, reason in enumerate(data.get("reasons", []), 1):
        elements.append(Paragraph(f"  {i}. {reason}", styles["BodyText2"]))
    elements.append(Spacer(1, 8))

    # Feature Breakdown
    elements.append(Paragraph("Feature Breakdown", styles["SectionHead"]))
    feat_header = ["Feature", "Value", "Importance"]
    feat_rows = [feat_header]
    for f in data.get("features", []):
        feat_rows.append([f["name"], str(f["value"]), f'{f["importance"]}%'])

    feat_table = Table(feat_rows, colWidths=[180, 80, 80])
    feat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f97316")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(feat_table)
    elements.append(Spacer(1, 20))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    elements.append(Spacer(1, 6))
    elements.append(
        Paragraph(
            "This report was generated by the Cyber Risk Intelligence System. "
            "Results are based on machine learning analysis and heuristic rules.",
            ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#94a3b8"),
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(elements)
    return filename


def generate_mail_report(message: str, data: dict) -> str:
    """Generate a PDF report for email analysis. Returns the filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mail_report_{timestamp}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=30 * mm,
        rightMargin=30 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=22,
            spaceAfter=6,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=20,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionHead",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=18,
            spaceAfter=8,
            textColor=colors.HexColor("#2563eb"),
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyText2",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=4,
            textColor=colors.HexColor("#1e293b"),
            leading=14,
        )
    )

    elements = []

    # Title
    elements.append(Paragraph("📧 Email Analysis Report", styles["ReportTitle"]))
    elements.append(
        Paragraph(
            f'Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}',
            styles["ReportSubtitle"],
        )
    )
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    elements.append(Spacer(1, 12))

    # Analysis Type
    elements.append(Paragraph("Analysis Type: Email / Message Scan", styles["SectionHead"]))

    # Message preview (truncated)
    preview = message[:500] + ("..." if len(message) > 500 else "")
    elements.append(Paragraph(f"<b>Message:</b> {preview}", styles["BodyText2"]))
    elements.append(Spacer(1, 8))

    # Results
    elements.append(Paragraph("Classification Results", styles["SectionHead"]))
    pred_color = colors.HexColor("#dc2626") if data["is_spam"] else colors.HexColor("#16a34a")

    result_data = [
        ["Prediction", "Confidence", "Spam Probability"],
        [data["prediction"], f"{data['confidence']}%", f"{data['spam_probability']}%"],
    ]
    result_table = Table(result_data, colWidths=[140, 120, 120])
    result_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f9fafb")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(result_table)
    elements.append(Spacer(1, 12))

    # Suspicious words
    if data.get("suspicious_words"):
        elements.append(Paragraph("Flagged Words", styles["SectionHead"]))
        elements.append(Paragraph(", ".join(data["suspicious_words"]), styles["BodyText2"]))
        elements.append(Spacer(1, 8))

    # Reasons
    elements.append(Paragraph("Findings", styles["SectionHead"]))
    for i, reason in enumerate(data.get("reasons", []), 1):
        elements.append(Paragraph(f"  {i}. {reason}", styles["BodyText2"]))
    elements.append(Spacer(1, 20))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
    elements.append(Spacer(1, 6))
    elements.append(
        Paragraph(
            "This report was generated by the Cyber Risk Intelligence System. "
            "Results are based on TF-IDF + Logistic Regression analysis.",
            ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#94a3b8"),
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(elements)
    return filename
