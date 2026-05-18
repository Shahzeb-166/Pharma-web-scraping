"""
pdf_generator.py — Weekly Pharma Intelligence Report PDF Builder
Primary colour: #039fe2 | Font: Times New Roman (Times-Roman in ReportLab)
Text colour: Black
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image, KeepTogether
)
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
import os

# ── COLOURS ───────────────────────────────────────────────────────────────────
C_PRIMARY   = HexColor("#039fe2")
C_PRIMARY_D = HexColor("#0276a8")
C_PRIMARY_L = HexColor("#e0f4fc")
C_PRIMARY_XL= HexColor("#f0faff")
C_GOLD      = HexColor("#f0a500")
C_BLACK     = HexColor("#1a1a1a")
C_WHITE     = colors.white
C_LIGHT_BG  = HexColor("#f0faff")
C_MID_GREY  = HexColor("#555555")
C_RULE      = HexColor("#b3dff5")

# ── FONTS — ReportLab built-in Times (= Times New Roman equivalent) ───────────
FONT_R  = "Times-Roman"
FONT_B  = "Times-Bold"
FONT_I  = "Times-Italic"
FONT_BI = "Times-BoldItalic"

W, H = A4
CONTENT_W = W - 30*mm  # usable text width


# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────

def build_styles():
    return {
        # Cover
        "cover_company": ParagraphStyle("cover_company",
            fontName=FONT_B, fontSize=11, textColor=C_WHITE,
            alignment=TA_CENTER, spaceAfter=2),
        "cover_title": ParagraphStyle("cover_title",
            fontName=FONT_B, fontSize=28, textColor=C_WHITE,
            alignment=TA_CENTER, leading=34, spaceAfter=6),
        "cover_sub": ParagraphStyle("cover_sub",
            fontName=FONT_I, fontSize=13, textColor=HexColor("#cceeff"),
            alignment=TA_CENTER, spaceAfter=4),
        "cover_date": ParagraphStyle("cover_date",
            fontName=FONT_R, fontSize=11, textColor=HexColor("#aaddee"),
            alignment=TA_CENTER),
        # Section banners
        "section_num": ParagraphStyle("section_num",
            fontName=FONT_B, fontSize=9, textColor=HexColor("#cceeff"),
            alignment=TA_LEFT),
        "section_title": ParagraphStyle("section_title",
            fontName=FONT_B, fontSize=14, textColor=C_WHITE,
            alignment=TA_LEFT, leading=18),
        # Sub-headings
        "sub_h": ParagraphStyle("sub_h",
            fontName=FONT_B, fontSize=11, textColor=C_PRIMARY_D,
            spaceBefore=6, spaceAfter=3),
        "sub_h2": ParagraphStyle("sub_h2",
            fontName=FONT_B, fontSize=10, textColor=C_BLACK,
            spaceBefore=4, spaceAfter=2),
        # Body text
        "body": ParagraphStyle("body",
            fontName=FONT_R, fontSize=9.5, textColor=C_BLACK,
            leading=15, spaceAfter=4, alignment=TA_JUSTIFY),
        "body_small": ParagraphStyle("body_small",
            fontName=FONT_R, fontSize=8.5, textColor=C_MID_GREY,
            leading=13, spaceAfter=2),
        "bullet": ParagraphStyle("bullet",
            fontName=FONT_R, fontSize=9.5, textColor=C_BLACK,
            leading=14, leftIndent=10, spaceAfter=3),
        # Article card
        "art_title": ParagraphStyle("art_title",
            fontName=FONT_B, fontSize=10, textColor=C_PRIMARY_D,
            spaceBefore=4, spaceAfter=2, leading=14),
        "art_body": ParagraphStyle("art_body",
            fontName=FONT_I, fontSize=9, textColor=C_BLACK,
            leading=14, spaceAfter=2, alignment=TA_JUSTIFY),
        "art_url": ParagraphStyle("art_url",
            fontName=FONT_R, fontSize=7.5, textColor=C_MID_GREY,
            spaceAfter=3),
        # Table headers
        "th": ParagraphStyle("th",
            fontName=FONT_B, fontSize=9, textColor=C_WHITE,
            alignment=TA_CENTER),
        "td": ParagraphStyle("td",
            fontName=FONT_R, fontSize=8.5, textColor=C_BLACK,
            alignment=TA_CENTER, leading=10),
        "td_left": ParagraphStyle("td_left",
            fontName=FONT_R, fontSize=8.5, textColor=C_BLACK,
            alignment=TA_LEFT, leading=10),
        # References
        "ref": ParagraphStyle("ref",
            fontName=FONT_R, fontSize=8, textColor=C_MID_GREY,
            leading=12, spaceAfter=2),
        # Footer
        "footer": ParagraphStyle("footer",
            fontName=FONT_R, fontSize=7, textColor=C_MID_GREY,
            alignment=TA_CENTER),
    }


# ─────────────────────────────────────────────────────────────────────────────
# REUSABLE COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

def section_banner(number, title, styles):
    """Full-width primary-colour section header banner."""
    inner = Table(
        [[Paragraph(f"SECTION {number}", styles["section_num"]),
          Paragraph(title, styles["section_title"])]],
        colWidths=[22*mm, CONTENT_W - 22*mm]
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), C_PRIMARY),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1), 10),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
    ]))
    return inner

def subsection_rule(title, styles):
    """Thin rule with sub-heading text."""
    return [
        HRFlowable(width="100%", thickness=1.2, color=C_PRIMARY, spaceAfter=2, spaceBefore=6),
        Paragraph(title, styles["sub_h"]),
    ]

def bullets(items, styles, max_n=8):
    return [Paragraph(f"&#8226; {str(i).strip()[:220]}", styles["bullet"])
            for i in items[:max_n] if str(i).strip()]

def article_card(title, url, summary, styles, show_summary=True):
    els = [Paragraph(title, styles["art_title"])]

    if show_summary and summary:
        els.append(Paragraph(summary[:450] + ("…" if len(summary) > 450 else ""), styles["art_body"]))

    if url:
        safe_url = url.replace("&", "&amp;")
        els.append(Paragraph(f'<link href="{safe_url}" color="blue">{safe_url}</link>', styles["art_url"]))

    return els

def _table_style_base():
    return TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  C_PRIMARY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_WHITE, C_PRIMARY_XL]),
        ("GRID",          (0,0),(-1,-1),  0.4, C_RULE),
        ("TOPPADDING",    (0,0),(-1,-1),  5),
        ("BOTTOMPADDING", (0,0),(-1,-1),  5),
        ("LEFTPADDING",   (0,0),(-1,-1),  5),
        ("RIGHTPADDING",  (0,0),(-1,-1),  5),
        ("ALIGN",         (0,0),(-1,-1),  "CENTER"),
        ("VALIGN",        (0,0),(-1,-1),  "MIDDLE"),
    ])

def chart_image(path, width_mm=160):
    """Insert a chart PNG if it exists."""
    if path and os.path.exists(path):
        return Image(path, width=width_mm*mm, height=width_mm*mm*0.5)
    return None

def safe_cell_text(value, maxlen=20):
    if value is None:
        return "—"
    text = str(value).strip()
    text = " ".join(text.split())
    if len(text) > maxlen:
        text = text[:maxlen] + "…"
    return text

# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER / FOOTER
# ─────────────────────────────────────────────────────────────────────────────

def make_header_footer(week_label, date_str):
    def draw(canvas, doc):
        canvas.saveState()

        if doc.page == 1:
            # Full cover banner - drawn in story, just add thin accent strip at bottom
            canvas.setFillColor(C_PRIMARY)
            canvas.rect(0, 0, W, 8*mm, fill=1, stroke=0)
            canvas.setFillColor(C_WHITE)
            canvas.setFont(FONT_R, 7)
            canvas.drawCentredString(W/2, 2.8*mm,
                "CONFIDENTIAL — Finance & Procurement Team   |   Not for External Distribution")
        else:
            # Top bar
            canvas.setFillColor(C_PRIMARY)
            canvas.rect(0, H-13*mm, W, 13*mm, fill=1, stroke=0)
            canvas.setFillColor(C_WHITE)
            canvas.setFont(FONT_B, 8.5)
            canvas.drawString(15*mm, H-8*mm, "PHARMA INTELLIGENCE WEEKLY")
            canvas.setFont(FONT_R, 8)
            canvas.drawRightString(W-15*mm, H-8*mm, f"Week: {week_label}  |  {date_str}")

            # Bottom bar
            canvas.setFillColor(C_PRIMARY_L)
            canvas.rect(0, 0, W, 9*mm, fill=1, stroke=0)
            canvas.setFillColor(C_MID_GREY)
            canvas.setFont(FONT_R, 7)
            canvas.drawCentredString(W/2, 3*mm,
                f"CONFIDENTIAL — Finance & Procurement   |   Page {doc.page}   |   {date_str}")

        canvas.restoreState()
    return draw


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PDF BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def info_box(title, lines, styles):
    """Light blue executive summary box (AI-ready)."""
    rows = [[Paragraph(f"<b>{title}</b>", styles["sub_h2"])]]
    for ln in lines:
        rows.append([Paragraph(f"• {ln}", styles["body_small"])])
    tbl = Table(rows, colWidths=[CONTENT_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), C_PRIMARY_XL),
        ("BOX",        (0,0),(-1,-1), 0.6, C_PRIMARY),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    return tbl

def generate_pdf(data: dict, chart_paths: dict, output_path: str):
    styles     = build_styles()
    week_label = data.get("week_label", "")
    date_str   = data.get("generated_at", "")

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=16*mm,  bottomMargin=12*mm,
    )
    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    # Background is drawn by header/footer callback (page 1 full bleed)
    # Add a tall spacer to push content into the centre of the blue zone
    story.append(Spacer(1, 68*mm))
    story.append(Paragraph("PHARMACEUTICAL INDUSTRY", styles["cover_company"]))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("WEEKLY INTELLIGENCE<br/>REPORT", styles["cover_title"]))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(f"Week of {week_label}", styles["cover_sub"]))
    story.append(Paragraph(date_str, styles["cover_date"]))
    story.append(Spacer(1, 10*mm))

    # Table of Contents box
    toc = Table([[Paragraph(
        "<b>CONTENTS</b><br/><br/>"
        "01 &nbsp; Economic Conditions — Pakistan &amp; Global<br/>"
        "02 &nbsp; Technology in the Pharmaceutical Industry<br/>"
        "03 &nbsp; New Products, Launches &amp; Disease Trends<br/>"
        "04 &nbsp; Technology Overall — Manufacturing &amp; Recycling<br/>"
        "05 &nbsp; References",
        ParagraphStyle("toc", fontName=FONT_R, fontSize=10.5, textColor=C_BLACK,
                       leading=20, alignment=TA_LEFT)
    )]], colWidths=[120*mm])
    toc.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_WHITE),
        ("BOX",           (0,0),(-1,-1), 1.5, C_PRIMARY),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 18),
        ("RIGHTPADDING",  (0,0),(-1,-1), 18),
    ]))
    story.append(toc)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # SECTION 1 — ECONOMIC CONDITIONS (EXECUTIVE SNAPSHOT — ONE PAGE)
    # ═══════════════════════════════════════════════════════════════
    
    eco = data.get("economic", {})
    
    story.append(section_banner(
        "01",
        "Economic Conditions — Weekly Snapshot",
        styles
    ))
    story.append(Spacer(1, 2*mm))
    
    # ─────────────────────────────────────────
    # EXECUTIVE SUMMARY (AI-READY PLACEHOLDER)
    # ─────────────────────────────────────────
    story.append(info_box(
        "Executive Economic Highlights",
        [
            "Foreign exchange remained under pressure with limited weekly relief.",
            "Fuel prices declined, easing near-term logistics and production cost pressure.",
            "Global energy and metals showed mixed movement amid demand uncertainty.",
            "No major new tax or inflation policy actions announced this week."
        ],
        styles
    ))
    
    story.append(Spacer(1, 3*mm))
    
    # ─────────────────────────────────────────
    # FOREX — TABLE + CHART
    # ─────────────────────────────────────────
    forex = eco.get("forex", {})
    open_mkt = forex.get("open_market", {})
    nbp = forex.get("nbp", {})
    
    fx_rows = [[
        Paragraph("Currency", styles["th"]),
        Paragraph("Open Buy", styles["th"]),
        Paragraph("Open Sell", styles["th"]),
        Paragraph("NBP Sell", styles["th"]),
    ]]
    
    for code in ["USD","EUR","GBP","CNY","SAR","AED"]:
        om = open_mkt.get(code, {})
        nb = nbp.get(code, {})
        if om or nb:
            fx_rows.append([
                Paragraph(code, styles["td"]),
                Paragraph(safe_cell_text(om.get("buy")), styles["td"]),
                Paragraph(safe_cell_text(om.get("sell")), styles["td"]),
                Paragraph(safe_cell_text(nb.get("sell")), styles["td"]),
            ])
    
    fx_table = Table(
        fx_rows,
        colWidths=[22*mm, 28*mm, 28*mm, 28*mm],
        repeatRows=1
    )
    fx_table.setStyle(_table_style_base())
    
    fx_chart = chart_image(chart_paths.get("forex"), width_mm=60)
    
    story.append(KeepTogether([
        Table(
            [[fx_table, fx_chart]],
            colWidths=[CONTENT_W*0.6, CONTENT_W*0.4],
            style=[("VALIGN",(0,0),(-1,-1),"TOP")]
        )
    ]))
    
    story.append(Spacer(1, 2*mm))
    
    # ─────────────────────────────────────────
    # FUEL — TABLE + CHART
    # ─────────────────────────────────────────
    fuel = eco.get("fuel", {})
    
    fuel_rows = [[
        Paragraph("Fuel", styles["th"]),
        Paragraph("Current", styles["th"]),
        Paragraph("Previous", styles["th"]),
    ]]
    
    for p in fuel.get("prices", []):
        prev = p.get("previous")
        fuel_rows.append([
            Paragraph(p.get("product",""), styles["td_left"]),
            Paragraph(p.get("price","—"), styles["td"]),
            Paragraph(f"Rs.{prev:.2f}" if isinstance(prev,(int,float)) else "—", styles["td"]),
        ])
    
    fuel_table = Table(
        fuel_rows,
        colWidths=[50*mm, 35*mm, 35*mm],
        repeatRows=1
    )
    fuel_table.setStyle(_table_style_base())
    
    fuel_chart = chart_image(chart_paths.get("fuel"), width_mm=60)
    
    story.append(KeepTogether([
        Table(
            [[fuel_table, fuel_chart]],
            colWidths=[CONTENT_W*0.6, CONTENT_W*0.4],
            style=[("VALIGN",(0,0),(-1,-1),"TOP")]
        )
    ]))
    
    story.append(Spacer(1, 2*mm))
    
    # ─────────────────────────────────────────
    # COMMODITIES — FULL WIDTH (CLEAN)
    # ─────────────────────────────────────────
    comms = eco.get("commodities", {})
    items = comms.get("energy", []) + comms.get("metals", [])
    
    comm_rows = [[
        Paragraph("Commodity", styles["th"]),
        Paragraph("Price", styles["th"]),
        Paragraph("Weekly Δ", styles["th"]),
    ]]
    
    for c in items:
        comm_rows.append([
            Paragraph(c.get("name",""), styles["td_left"]),
            Paragraph(f"{c.get('price','')} {c.get('unit','')}", styles["td"]),
            Paragraph(c.get("weekly",""), styles["td"]),
        ])
    
    comm_table = Table(
        comm_rows,
        colWidths=[60*mm, 70*mm, 30*mm],
        repeatRows=1
    )
    comm_table.setStyle(_table_style_base())
    
    story.append(KeepTogether([comm_table]))
    
    story.append(Spacer(1, 2*mm))
    
    # ─────────────────────────────────────────
    # INFLATION & TAX — TEXT (2 COLUMNS)
    # ─────────────────────────────────────────
    inf = eco.get("inflation", {})
    
    left, right = [], []
    
    if inf.get("sbp_highlights"):
        left.append(Paragraph("<b>SBP & Inflation</b>", styles["sub_h2"]))
        left.extend(bullets(inf["sbp_highlights"], styles, max_n=3))
    
    if inf.get("fbr_sros"):
        left.append(Spacer(1,1*mm))
        left.append(Paragraph("<b>Tax & SRO Updates</b>", styles["sub_h2"]))
        left.extend(bullets(inf["fbr_sros"], styles, max_n=3))
    
    pwc = inf.get("pwc_developments", {})
    if pwc.get("content"):
        right.append(Paragraph("<b>PwC — Key Developments</b>", styles["sub_h2"]))
        right.append(Paragraph(pwc["content"][:550] + "...", styles["body_small"]))
    
    story.append(KeepTogether([
        Table(
            [[left, right]],
            colWidths=[CONTENT_W*0.5, CONTENT_W*0.5],
            style=[("VALIGN",(0,0),(-1,-1),"TOP"),
                   ("LEFTPADDING",(0,0),(-1,-1),6),
                   ("RIGHTPADDING",(0,0),(-1,-1),6)]
        )
    ]))
    
    # FORCE SECTION TO END ON SAME PAGE
    story.append(PageBreak())


    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — TECHNOLOGY IN PHARMA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_banner("02", "Technology in the Pharmaceutical Industry", styles))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "This section covers emerging technologies being adopted by the pharmaceutical industry "
        "globally and in Pakistan — including AI, blockchain, automation, IoT, digital twins, "
        "and advanced manufacturing techniques.",
        styles["body"]))
    story.append(Spacer(1, 3*mm))

    pharma_tech = data.get("pharma_tech", {})

    img4 = chart_image(chart_paths.get("pharma_tech"))
    if img4:
        story.append(img4)
        story.append(Spacer(1, 3*mm))

    # Articles with summaries
    story.extend(subsection_rule("Health and Pharmatech NEWS", styles))
    for art in pharma_tech.get("articles", [])[:50]:
        story.extend(article_card(art.get("title",""), art.get("url",""),
                                  art.get("summary",""), styles))
        story.append(Spacer(1, 1*mm))

    # Academic research
    research = pharma_tech.get("research", [])
    if research:
        story.extend(subsection_rule("Academic Research (Google Scholar)", styles))
        for r in research[:20]:
            story.append(Paragraph(f"&#8226; {r.get('title','')}", styles["bullet"]))
            if r.get("url"):
                story.append(Paragraph(r["url"], styles["art_url"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — NEW PRODUCT LAUNCHES & DISEASE TRENDS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_banner("03", "New Products and Latest Research", styles))
    story.append(Spacer(1, 4*mm))

    np_data = data.get("new_products", {})

    # # DRAP approvals
    # drap_items = np_data.get("drap_approvals", [])
    # if drap_items:
    #     story.extend(subsection_rule("DRAP — Registrations & Public Health Alerts", styles))
    #     for item in drap_items[:6]:
    #         title = item.get("title", "") if isinstance(item, dict) else str(item)
    #         url = item.get("url", "") if isinstance(item, dict) else ""
    #         date = item.get("date", "") if isinstance(item, dict) else ""

    #         if url:
    #             safe_url = url.replace("&", "&amp;")
    #             story.append(
    #                 Paragraph(
    #                     f'&#8226; {title} ({date})<br/><link href="{safe_url}" color="blue">{safe_url}</link>',
    #                     styles["bullet"]
    #                 )
    #             )
    #         else:
    #             story.append(Paragraph(f'&#8226; {title}', styles["bullet"]))

    # New launches
    launches = np_data.get("launches", [])
    if launches:
        story.extend(subsection_rule("New Product Launches — Pakistan", styles))
        for art in launches[:5]:
            story.extend(article_card(art.get("title",""), art.get("url",""),
                                      art.get("summary",""), styles))

    # Global pipeline
    pipeline = np_data.get("pipeline", [])
    if pipeline:
        story.extend(subsection_rule("Global Drug Pipeline & Approvals", styles))
        for p in pipeline[:6]:
            story.append(Paragraph(f"&#8226; {p.get('title','')}", styles["bullet"]))
            if p.get("url"):
                story.append(Paragraph(p["url"], styles["art_url"]))

    # Disease trends
    story.extend(subsection_rule("Disease Trends — Pakistan & Global", styles))
    trends = np_data.get("disease_trends", [])
    if trends:
        story.extend(bullets(trends, styles))

    img5 = chart_image(chart_paths.get("disease"))
    if img5:
        story.append(Spacer(1, 3*mm))
        story.append(img5)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — TECHNOLOGY OVERALL
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_banner("04", "Technology Overall — Manufacturing, Recycling & Industry", styles))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Covering the latest technology developments across industries — with a focus on "
        "manufacturing innovations, recycling and sustainable production techniques relevant "
        "to pharmaceutical and allied industries.",
        styles["body"]))
    story.append(Spacer(1, 3*mm))

    gen_tech = data.get("gen_tech", {})

    # Emerging tech
    em_tech = gen_tech.get("emerging_tech", [])
    if em_tech:
        story.extend(subsection_rule("Emerging Technologies in Industry", styles))
        for art in em_tech[:5]:
            story.extend(article_card(art.get("title",""), art.get("url",""),
                                      art.get("summary",""), styles))

    # Manufacturing
    mfg = gen_tech.get("manufacturing", [])
    if mfg:
        story.extend(subsection_rule("Advanced Manufacturing", styles))
        for m in mfg[:5]:
            story.append(Paragraph(f"&#8226; {m.get('title','')}", styles["bullet"]))
            if m.get("url"):
                story.append(Paragraph(m["url"], styles["art_url"]))

    # Recycling
    rec = gen_tech.get("recycling", [])
    if rec:
        story.extend(subsection_rule("Recycling & Circular Economy", styles))
        for r in rec[:5]:
            if isinstance(r, dict):
                story.extend(article_card(
                    r.get("title", ""),
                    r.get("url", ""),
                    r.get("summary", ""),
                    styles
                ))
            else:
                story.append(Paragraph(f"&#8226; {str(r)}", styles["bullet"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # REFERENCES PAGE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_banner("05", "References", styles))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        "All data, articles and information in this report were sourced from the following "
        "publicly available pages as of the generation date.",
        styles["body"]))
    story.append(Spacer(1, 4*mm))

    refs = data.get("all_references", [])
    if refs:
        ref_rows = [[
            Paragraph("#", styles["th"]),
            Paragraph("URL", styles["th"]),
        ]]
        for i, url in enumerate(refs, 1):
            ref_rows.append([
                Paragraph(str(i), styles["td"]),
                Paragraph(f'<link href="{url.replace("&", "&amp;")}" color="blue">{url}</link>', styles["ref"])            ])
        rt = Table(ref_rows, colWidths=[12*mm, CONTENT_W - 12*mm])
        rt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),  C_PRIMARY),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_WHITE, C_PRIMARY_XL]),
            ("GRID",          (0,0),(-1,-1),  0.3, C_RULE),
            ("TOPPADDING",    (0,0),(-1,-1),  4),
            ("BOTTOMPADDING", (0,0),(-1,-1),  4),
            ("LEFTPADDING",   (0,0),(-1,-1),  4),
            ("RIGHTPADDING",  (0,0),(-1,-1),  4),
            ("VALIGN",        (0,0),(-1,-1),  "TOP"),
            ("ALIGN",         (0,0),(0,-1),   "CENTER"),
        ]))
        story.append(rt)

    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=3))
    story.append(Paragraph(
        "This report is auto-generated for internal use only. "
        "Verify all critical figures from official sources before financial decisions. "
        "© Pharma Intelligence Weekly — Finance &amp; Procurement Division.",
        styles["body_small"]))

    # ── BUILD ─────────────────────────────────────────────────────────────────
    hf = make_header_footer(week_label, date_str)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    print(f"  PDF saved → {output_path}")
    return output_path
