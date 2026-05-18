"""
main_render.py
HTML/CSS → PDF renderer (DATA + CHARTS)
"""

from pathlib import Path
from typing import Dict
from playwright.async_api import async_playwright
import asyncio
from weather import (
    fetch_weather,
    render_today_weather_widget,
    render_week_weather_cards
)

from pathlib import Path
from pathlib import Path
from urllib.parse import quote



BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "templates"
STYLE_DIR = BASE_DIR / "styles"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# HTML HELPERS
# --------------------------------------------------

def build_table(headers, rows) -> str:
    ths = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows
    )

    return f"""
    <table>
      <thead><tr>{ths}</tr></thead>
      <tbody>{trs}</tbody>
    </table>
    """


def build_list(items) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"



def img_tag(path: str, width="100%") -> str:
    if not path:
        return ""

    # Convert to absolute path
    p = Path(path).absolute()

    # Build correct file:/// URI with URL-safe encoding
    uri = "file:///" + quote(str(p).replace("\\", "/"))

    return f'<img src="{uri}" style="width:{width}; max-width:100%;" />'

# --------------------------------------------------
# ECONOMIC SECTION RENDERING
# --------------------------------------------------

def render_economic_section(data: dict, chart_paths: dict) -> dict:
    eco = data.get("economic", {})
    inf = eco.get("inflation", {})
    dawn_pakistan = inf.get("dawn_pakistan", [])


    def ul(items):
        if not items:
            return "<p>No significant updates this week.</p>"
        return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

    def table(headers, rows):
        thead = "".join(f"<th>{h}</th>" for h in headers)
        tbody = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
            for row in rows
        )
        return f"""
        <table>
          <thead><tr>{thead}</tr></thead>
          <tbody>{tbody}</tbody>
        </table>
        """

    # =========================
    # FOREX TABLE
    # =========================
    forex = eco.get("forex", {})
    open_mkt = forex.get("open_market", {})
    nbp = forex.get("nbp", {})

    fx_rows = []
    for code in ["USD", "EUR", "GBP", "CNY", "SAR", "AED"]:
        om = open_mkt.get(code, {})
        nb = nbp.get(code, {})
        if om or nb:
            fx_rows.append([
                code,
                om.get("buy", "—"),
                om.get("sell", "—"),
            ])

    forex_table = table(
        ["Currency", "Open Buy", "Open Sell"],
        fx_rows
    )

    # =========================
    # FUEL TABLE
    # =========================
    fuel_rows = []
    for p in eco.get("fuel", {}).get("prices", []):
        prev = p.get("previous")
        fuel_rows.append([
            p.get("product", ""),
            p.get("price", "—"),
            f"Rs.{prev:.2f}" if isinstance(prev, (int, float)) else "—",
            p.get("change"),
        ])

    fuel_table = table(
        ["Fuel", "Current", "Previous","Change"],
        fuel_rows
    )

    # =========================
    # COMMODITIES TABLE
    # =========================
    comms = eco.get("commodities", {})
    items = comms.get("energy", []) + comms.get("metals", [])

    comm_rows = []
    for c in items:
        comm_rows.append([
            c.get("name", ""),
            f"{c.get('price','')} {c.get('unit','')}",
            c.get("weekly", ""),
        ])

    commodities_table = table(
        ["Commodity", "Price", "Weekly Δ"],
        comm_rows
    )

    # =========================
    # AI SUMMARIES (STATIC FOR NOW)
    # =========================
    # overall_ai_summary = ul([
    #     "PKR remained under pressure amid macroeconomic uncertainty.",
    #     "Fuel prices declined, providing short-term cost relief.",
    #     "Energy and metals commodities showed mixed global signals.",
    #     "No major fiscal or monetary policy surprise this week."
    # ])
    #
    # forex_ai_summary = ul([
    #     "Foreign exchange markets remained volatile with limited improvement."
    # ])
    #
    # fuel_ai_summary = ul([
    #     "Fuel price corrections may ease logistics and distribution costs."
    # ])
    #
    # commodities_ai_summary = ul([
    #     "Energy prices were mixed; metals showed selective strength."
    # ])
    #
    # inflation_ai_summary = ul([
    #     "Inflation remains sticky with cautious monetary outlook.",
    #     "Policy stance remains unchanged."
    # ])

    # =========================
    # TAX / PWC HANDLING (DICT SAFE)
    # =========================
    pwc_dev = inf.get("pwc_developments", {})
    pwc_text = pwc_dev.get("content", "")

    tax_points = ul([
        s.strip() + "." for s in pwc_text.split(".")
        if len(s.strip()) > 40
    ][:4])

    # tax_ai_summary = ul([
    #     "Corporate tax structure adjusted under Finance Act 2025.",
    #     "Higher withholding taxes on banking and digital transactions.",
    #     "Incentives and exemptions rationalized."
    # ])
    # =========================
    # PWC DEVELOPMENTS (DICT SAFE)
    # =========================
    pwc_dev = inf.get("pwc_developments", {})
    pwc_text = pwc_dev.get("content", "").strip()
    pwc_title = pwc_dev.get("title", "PwC Developments")
    pwc_reviewed = pwc_dev.get("last_reviewed", "")
    
    # Turn long text into concise bullet candidates (pre-AI)
    pwc_bullets = [
        s.strip() + "."
        for s in pwc_text.split(".")
        if len(s.strip()) > 50
    ][:10]
    
    pwc_summary = ul(pwc_bullets)
    
    # =========================
    # PWC CORPORATE TAX TABLE
    # =========================
    pwc_tax_rows = []
    for row in inf.get("pwc_corporate_tax", []):
        pwc_tax_rows.append([
            row.get("company_type", ""),
            row.get("tax_rate", "") + "%"
        ])
    
    pwc_tax_table = table(
        ["Company Type", "Corporate Tax Rate"],
        pwc_tax_rows
    )
    
    global_data = eco.get("global", {})
    drap_data = eco.get("drap_updates", {})
    
    
    dawn_pakistan_block = build_dawn_articles(
        inf.get("dawn_pakistan", [])
    )

    brecorder_articles = build_brecorder_articles(
        inf.get("brecorder_econ", [])
    )
    
    # =========================
    # WEATHER INFORMATION
    # =========================
        
    weather = fetch_weather()
    
    today_weather_html = render_today_weather_widget(
        weather["current"],
        weather["daily"]
    )
    
    week_weather_html = render_week_weather_cards(
        weather["daily"]
    )
    
    pharma_data = data.get("new_products", {})
    pharma_tech = data.get("pharma_tech", {})
    
    launches = pharma_data.get("launches", [])
    pipeline = pharma_data.get("pipeline", [])
    
    tech_articles = pharma_tech.get("articles", [])
    tech_research = pharma_tech.get("research", [])


    # =========================
    # RETURN ALL PLACEHOLDERS
    # =========================
    return {
        
        "today_weather": today_weather_html,
        "week_weather": week_weather_html,

        # "overall_ai_summary": overall_ai_summary,
        #
        # "forex_ai_summary": forex_ai_summary,
        # "fuel_ai_summary": fuel_ai_summary,
        # "commodities_ai_summary": commodities_ai_summary,
        #
        # "inflation_ai_summary": inflation_ai_summary,
        # "tax_ai_summary": tax_ai_summary,

        "forex_table": forex_table,
        "fuel_table": fuel_table,
        "commodities_table": commodities_table,

        "inflation_points": ul(inf.get("sbp_highlights", [])),
        "tax_points": tax_points,
        "pwc_tax_table":pwc_tax_table,
        "pwc_summary":pwc_summary,
        "dawn_pakistan": dawn_pakistan_block,

        "forex_chart": img_tag(chart_paths.get("forex")),
        "fuel_chart": img_tag(chart_paths.get("fuel")),
        "commodities_chart": img_tag(chart_paths.get("commodities")),
        
        "drug_launches": build_drug_launches(launches),
        "top_drugs_table": build_top_drugs_table(launches),
        "research_articles": build_research_articles(pipeline),
        "pharma_tech_articles": build_pharma_tech_articles(tech_articles),
        "pharma_research": build_pharma_research(tech_research),
        
        "economic_ai_summary": build_list(data.get("economic_ai_summary", "").split("\n")),
        "tech_ai_summary": build_list(data.get("tech_ai_summary", "").split("\n")),
        "disease_ai_summary": build_list(data.get("disease_ai_summary", "").split("\n")),
        "research_ai_summary": build_list(data.get("research_ai_summary", "").split("\n")),
        "global_ai_summary": build_list(data.get("global_ai_summary", "").split("\n")),
    
        "global_articles": build_article_list(global_data.get("articles", [])),
        "brecorder_econ": brecorder_articles,
    
        "drap_updates": build_drap_updates(drap_data.get("items", [])),
        "drap_source": drap_data.get("source", ""),

    }

def build_article_list(articles):
    if not articles:
        return "<p>No significant updates this week.</p>"

    html = ""
    for art in articles[:12]:  # limit for readability
        region = art.get("region", "Global")
        title = art.get("title", "")
        url = art.get("url", "#")

        html += f"""
        <div class="news-item">
          <span class="tag">{region}</span>
          <a href="{url}" target="_blank">{title}</a>
        </div>
        """

    return html

def build_dawn_articles(items):
    if not items:
        return "<p>No significant Pakistan economic developments this week.</p>"

    html = ""
    for art in items[:10]:
        title = art.get("title", "")
        url = art.get("url", "#")
        summary = art.get("summary", "")
        updated = art.get("last_updated", "")

        html += f"""
        <div class="news-item">
        {url}<b>{title}</b></a>
          <p class="summary">{summary}</p>
          <span class="meta">Updated: {updated}</span>
        </div>
        """

    return html

def build_brecorder_articles(articles):
    if not articles:
        return "<p>No significant BRecorder developments this week.</p>"

    html = ""
    for art in articles[:10]:
        title = art.get("title", "")
        url = art.get("url", "#")
        summary = art.get("summary", "")

        html += f"""
        <div class="news-item">
          <a href="{url}" target="_blank"><b>{title}</b></a>
          <p class="summary">{summary}</p>
        </div>
        """

    return html

from datetime import datetime

def build_drap_updates(items):
    if not items:
        return "<p>No recent DRAP updates.</p>"

    html = "<ul class='reg-list'>"
    for it in items[:10]:
        title = it.get("title", "")
        url = it.get("url", "#")
        date = it.get("date", "")

        try:
            date = datetime.fromisoformat(date).strftime("%d %b %Y")
        except:
            pass

        html += f"""
        <li>
          <a href="{url}" target="_blank">{title}</a>
          <span class="date">{date}</span>
        </li>
        """

    html += "</ul>"
    return html

def build_drug_launches(items):
    launches = [i for i in items if i.get("type") == "drug_to_watch_2026"]

    if not launches:
        return "<p>No new drug insights this week.</p>"

    html = ""
    for d in launches:
        html += f"""
        <div class="news-item">
          <span class="tag">Future Drug</span>
          <b>{d.get("drug","")}</b>
        </div>
        """

    return html

def build_top_drugs_table(items):
    rows = [i for i in items if i.get("type") == "top_selling_2025"]

    if not rows:
        return "<p>No top drug data available.</p>"

    headers = ["Rank", "Drug", "Manufacturer", "FY2025 ($M)"]

    table_rows = []
    for r in rows[:10]:
        table_rows.append([
            r.get("rank", ""),
            r.get("drug", ""),
            r.get("manufacturer", ""),
            r.get("fy2025", "")
        ])

    return build_table(headers, table_rows)


def build_research_articles(items):
    research = [i for i in items if i.get("type") == "research_article"]

    if not research:
        return "<p>No research updates this week.</p>"

    html = ""

    for art in research[:15]:
        html += f"""
        <div class="news-item">
          <span class="tag">{art.get("journal","")}</span>
          <a href="{art.get("url","#")}" target="_blank">
            <b>{art.get("title","")}</b>
          </a>
          <p class="summary">{art.get("summary","")}</p>
          <span class="meta">
            {art.get("article_type","")} | {art.get("date","")}
          </span>
        </div>
        """

    return html


def build_pharma_tech_articles(items):
    if not items:
        return "<p>No pharma technology updates this week.</p>"

    html = ""

    for art in items[:12]:
        html += f"""
        <div class="news-item">
          <span class="tag">Tech</span>
          <a href="{art.get("url","#")}" target="_blank">
            <b>{art.get("title","")}</b>
          </a>
          <p class="summary">{art.get("summary","")}</p>
        </div>
        """

    return html

def build_pharma_research(items):
    if not items:
        return "<p>No pharma research updates this week.</p>"

    html = ""

    for art in items[:12]:
        html += f"""
        <div class="news-item">
          <span class="tag">Research</span>
          <a href="{art.get("url","#")}" target="_blank">
            <b>{art.get("title","")}</b>
          </a>
          <p class="summary">{art.get("summary","")}</p>
        </div>
        """

    return html


# --------------------------------------------------
# HTML → PDF
# --------------------------------------------------
from datetime import datetime
from playwright.async_api import async_playwright

async def render_pdf_async(data: dict, chart_paths: dict, output_path: str):
    template_path = TEMPLATE_DIR / "economic.html"
    css_path = STYLE_DIR / "theme.css"

    # Load base HTML
    html = template_path.read_text(encoding="utf-8")

    # -------------------------------------
    # Render dynamic sections (tables, AI, charts)
    # -------------------------------------
    sections = render_economic_section(data, chart_paths)

    for key, val in sections.items():
        html = html.replace(f"{{{{ {key} }}}}", val)

    # -------------------------------------
    # Inject generated_at timestamp
    # -------------------------------------
    generated_at = datetime.now().strftime("%d %b %Y | %H:%M PKT")
    html = html.replace("{{ generated_at }}", generated_at)

    # -------------------------------------
    # Resolve CSS path for Playwright
    # -------------------------------------
    html = html.replace("../styles/theme.css", css_path.as_uri())

    # -------------------------------------
    # Write temporary HTML for debugging/rendering
    # -------------------------------------
    temp_html = OUTPUT_DIR / "__render.html"
    temp_html.write_text(html, encoding="utf-8")

    # -------------------------------------
    # Render PDF via Playwright (async-safe)
    # -------------------------------------
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(temp_html.as_uri(), wait_until="networkidle")

        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={
                "top": "18mm",
                "bottom": "18mm",
                "left": "18mm",
                "right": "18mm",
            },
        )

        await browser.close()
def img_tag(path: str, width="100%") -> str:
    if not path:
        return ""
    uri = Path(path).absolute().as_uri()
    return f'<img src="{uri}" style="width:{width}; max-width:100%;" />'


def render_pdf(data: dict, chart_paths: dict, output_path: str):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside asyncio → schedule task
        return asyncio.create_task(
            render_pdf_async(data, chart_paths, output_path)
        )
    else:
        # Normal execution
        return asyncio.run(
            render_pdf_async(data, chart_paths, output_path)
        )
