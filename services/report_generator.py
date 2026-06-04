import io
import logging
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

logger = logging.getLogger(__name__)

# ── Brand colours ─────────────────────────────────────────────────────────────
C_PRIMARY  = colors.HexColor("#2563eb")
C_ACCENT   = colors.HexColor("#7c3aed")
C_GREEN    = colors.HexColor("#16a34a")
C_RED      = colors.HexColor("#dc2626")
C_YELLOW   = colors.HexColor("#d97706")
C_DARK     = colors.HexColor("#1e293b")
C_LIGHT    = colors.HexColor("#f8fafc")
C_BORDER   = colors.HexColor("#e2e8f0")
C_MUTED    = colors.HexColor("#64748b")


def _styles():
    base = getSampleStyleSheet()
    extra = {
        "Title": ParagraphStyle("Title", parent=base["Normal"],
            fontSize=26, textColor=C_PRIMARY, spaceAfter=4, fontName="Helvetica-Bold",
            alignment=TA_CENTER),
        "Subtitle": ParagraphStyle("Subtitle", parent=base["Normal"],
            fontSize=11, textColor=C_MUTED, spaceAfter=18, alignment=TA_CENTER),
        "SectionHead": ParagraphStyle("SectionHead", parent=base["Normal"],
            fontSize=13, textColor=C_DARK, spaceBefore=16, spaceAfter=6,
            fontName="Helvetica-Bold"),
        "Body": ParagraphStyle("Body", parent=base["Normal"],
            fontSize=9.5, textColor=C_DARK, spaceAfter=4, leading=14),
        "Bullet": ParagraphStyle("Bullet", parent=base["Normal"],
            fontSize=9.5, textColor=C_DARK, leftIndent=14, spaceAfter=3,
            leading=13, bulletIndent=6),
        "Small": ParagraphStyle("Small", parent=base["Normal"],
            fontSize=8.5, textColor=C_MUTED, spaceAfter=2),
        "OriginalBullet": ParagraphStyle("OriginalBullet", parent=base["Normal"],
            fontSize=9, textColor=C_MUTED, leftIndent=14, spaceAfter=2,
            leading=12, italics=1),
        "ImprovedBullet": ParagraphStyle("ImprovedBullet", parent=base["Normal"],
            fontSize=9.5, textColor=C_GREEN, leftIndent=14, spaceAfter=6,
            leading=13, fontName="Helvetica-Bold"),
    }
    return extra


def _score_color(score: int):
    if score >= 70:
        return C_GREEN
    if score >= 45:
        return C_YELLOW
    return C_RED


def _rec_color(rec: str):
    if "Strong" in rec:
        return C_GREEN
    if "Moderate" in rec:
        return C_YELLOW
    return C_RED


def _bullet_items(items: list, style, prefix="•") -> list:
    return [Paragraph(f"{prefix}  {item}", style) for item in items if item]


def generate_pdf(report: dict) -> bytes:
    """
    Generate a professional PDF report from the stored report dict.
    Returns raw PDF bytes.
    """
    analysis = report.get("analysis", {})
    metadata = {
        "filename": report.get("filename", "resume.pdf"),
        "semantic_score": report.get("semantic_score"),
        "generated": datetime.now().strftime("%B %d, %Y at %H:%M"),
    }

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=1.8*cm, bottomMargin=1.8*cm,
        leftMargin=2*cm, rightMargin=2*cm,
        title="ResumeIQ Analysis Report",
        author="ResumeIQ",
    )

    S = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("ResumeIQ", S["Title"]))
    story.append(Paragraph("AI-Powered Resume Analysis Report", S["Subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=C_PRIMARY, spaceAfter=10))
    story.append(Paragraph(
        f"<b>File:</b> {metadata['filename']}  &nbsp;&nbsp; "
        f"<b>Generated:</b> {metadata['generated']}",
        S["Small"]))
    story.append(Spacer(1, 10))

    # ── Recommendation banner ─────────────────────────────────────────────────
    rec  = analysis.get("recommendation", "N/A")
    rec_reason = analysis.get("recommendation_reason", "")
    rec_color  = _rec_color(rec)
    banner_data = [[
        Paragraph(f'<font color="white"><b>{rec}</b></font>', ParagraphStyle(
            "Rec", fontSize=13, textColor=colors.white, fontName="Helvetica-Bold")),
        Paragraph(f'<font color="white">{rec_reason}</font>', ParagraphStyle(
            "RecReason", fontSize=9, textColor=colors.white, leading=13)),
    ]]
    banner_table = Table(banner_data, colWidths=["30%", "70%"])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), rec_color),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0,0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 14))

    # ── Score Summary ─────────────────────────────────────────────────────────
    story.append(Paragraph("Score Summary", S["SectionHead"]))

    scores = [
        ("Overall Match",  analysis.get("overall_score",  0)),
        ("ATS Score",      analysis.get("ats_score",      0)),
        ("Skills Match",   analysis.get("skills_score",   0)),
        ("Experience",     analysis.get("experience_score", 0)),
        ("Education",      analysis.get("education_score", 0)),
    ]
    if metadata["semantic_score"] is not None:
        scores.append(("Semantic Similarity", int(metadata["semantic_score"])))

    score_rows = [["Metric", "Score", "Rating"]]
    for label, val in scores:
        col = _score_color(val)
        rating = "Strong" if val >= 70 else "Moderate" if val >= 45 else "Needs Work"
        score_rows.append([
            Paragraph(label, S["Body"]),
            Paragraph(f'<font color="{col.hexval()}" size="11"><b>{val}%</b></font>',
                      ParagraphStyle("SC", fontSize=11, fontName="Helvetica-Bold")),
            Paragraph(f'<font color="{col.hexval()}">{rating}</font>', S["Body"]),
        ])

    t = Table(score_rows, colWidths=["50%", "25%", "25%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), C_DARK),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, colors.white]),
        ("GRID",         (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # ── Skills Analysis ───────────────────────────────────────────────────────
    story.append(Paragraph("Skills Analysis", S["SectionHead"]))

    found   = analysis.get("found_skills",   [])
    missing = analysis.get("missing_skills", [])

    skills_data = [
        [Paragraph("<b>Found Skills</b>", S["Body"]),
         Paragraph("<b>Missing Skills</b>", S["Body"])],
        [
            Paragraph(
                "  ".join(f'<font color="{C_GREEN.hexval()}">[+] {s}</font>' for s in found) or "None",
                ParagraphStyle("FC", fontSize=9, leading=14)),
            Paragraph(
                "  ".join(f'<font color="{C_RED.hexval()}">[-] {s}</font>' for s in missing) or "None",
                ParagraphStyle("MC", fontSize=9, leading=14)),
        ],
    ]
    st = Table(skills_data, colWidths=["50%", "50%"])
    st.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), C_BORDER),
        ("GRID",         (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(st)
    story.append(Spacer(1, 12))

    # ── Strengths & Weaknesses ────────────────────────────────────────────────
    story.append(Paragraph("Strengths & Weaknesses", S["SectionHead"]))
    sw_data = [
        [Paragraph("<b>Strengths</b>", S["Body"]),
         Paragraph("<b>Weaknesses</b>", S["Body"])],
        [
            [Paragraph(f"[+] {s}", ParagraphStyle("SItem", fontSize=9, textColor=C_GREEN,
                leftIndent=4, spaceAfter=3, leading=12))
             for s in analysis.get("strengths", [])],
            [Paragraph(f"[-] {w}", ParagraphStyle("WItem", fontSize=9, textColor=C_RED,
                leftIndent=4, spaceAfter=3, leading=12))
             for w in analysis.get("weaknesses", [])],
        ]
    ]
    sw = Table(sw_data, colWidths=["50%", "50%"])
    sw.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), C_BORDER),
        ("GRID",         (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(sw)
    story.append(Spacer(1, 12))

    # ── ATS & Improvement Tips ────────────────────────────────────────────────
    story.append(Paragraph("ATS Optimization Tips", S["SectionHead"]))
    story.extend(_bullet_items(analysis.get("ats_tips", []), S["Bullet"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Resume Improvement Recommendations", S["SectionHead"]))
    story.extend(_bullet_items(analysis.get("improvements", []), S["Bullet"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Missing ATS Keywords", S["SectionHead"]))
    kw = analysis.get("missing_keywords", [])
    if kw:
        story.append(Paragraph(
            "  |  ".join(f'<font color="{C_RED.hexval()}">{k}</font>' for k in kw),
            ParagraphStyle("KW", fontSize=9, leading=14, spaceAfter=8)))
    story.append(Spacer(1, 8))

    # ── Bullet Rewrites ───────────────────────────────────────────────────────
    rewrites = analysis.get("bullet_rewrites", [])
    if rewrites:
        story.append(Paragraph("Improved Resume Bullet Points", S["SectionHead"]))
        for i, rw in enumerate(rewrites[:7], 1):
            orig = rw.get("original", "")
            improved = rw.get("improved", "")
            if orig and improved:
                story.append(Paragraph(f"<i>Original {i}:</i>  {orig}", S["OriginalBullet"]))
                story.append(Paragraph(f">> {improved}", S["ImprovedBullet"]))
        story.append(Spacer(1, 8))

    # ── Interview Questions ───────────────────────────────────────────────────
    iq = analysis.get("interview_questions", {})
    if any(iq.values()):
        story.append(Paragraph("Personalized Interview Questions", S["SectionHead"]))
        for q_type, label in [
            ("technical",     "Technical"),
            ("behavioral",    "Behavioral"),
            ("project_based", "Project-Based"),
            ("scenario_based","Scenario-Based"),
        ]:
            qs = iq.get(q_type, [])
            if qs:
                story.append(Paragraph(f"<b>{label}</b>", S["Body"]))
                story.extend(_bullet_items(qs, S["Bullet"], prefix="Q."))
        story.append(Spacer(1, 8))

    # ── Learning Roadmap ──────────────────────────────────────────────────────
    roadmap = analysis.get("learning_roadmap", [])
    if roadmap:
        story.append(Paragraph("Learning Roadmap", S["SectionHead"]))
        rm_rows = [["Week", "Topic", "Description", "Category"]]
        for item in roadmap:
            rm_rows.append([
                Paragraph(f"Week {item.get('week', '')}", S["Small"]),
                Paragraph(f"<b>{item.get('topic', '')}</b>", S["Body"]),
                Paragraph(item.get("description", ""), S["Small"]),
                Paragraph(item.get("skill_category", ""), S["Small"]),
            ])
        rm = Table(rm_rows, colWidths=["10%", "22%", "50%", "18%"])
        rm.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, colors.white]),
            ("GRID",         (0, 0), (-1, -1), 0.5, C_BORDER),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ]))
        story.append(rm)
        story.append(Spacer(1, 8))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER))
    story.append(Paragraph(
        "Generated by <b>ResumeIQ</b> — AI Resume Analyzer powered by Google Gemini",
        ParagraphStyle("Footer", fontSize=8, textColor=C_MUTED,
                       alignment=TA_CENTER, spaceAfter=0)))

    try:
        doc.build(story)
        return buf.getvalue()
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        raise
