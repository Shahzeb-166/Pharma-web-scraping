"""
scraper.py — Weekly Pharma Intelligence Report — Data Collector
Sections:
  1. Economic Conditions (Pakistan + Global)
  2. Technology in Pharma
  3. New Product Launches & Disease Trends
  4. Technology Overall
"""

import requests, re, io, json, os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
import time,sys
import threading
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import asyncio


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "last_week.json")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
def safe_get(url, timeout=20, raw=False):
    time.sleep(1.2)

    session = requests.Session()
    session.headers.update({
        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36",
        "Accept":
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.google.com/",
    })

    try:
        r = session.get(url, timeout=timeout)

        # Explicit bot-block detection
        if r.status_code == 403:
            raise PermissionError("403 Forbidden")

        r.raise_for_status()

        if raw:
            return r

        return BeautifulSoup(r.text, "lxml")

    except PermissionError:
        print(f"    [BOT] 403 detected → switching to Playwright: {url}")
        return playwright_fallback(url)

    except Exception as e:
        print(f"    [WARN] {url[:70]} → {e}")
        return None
    


def playwright_fallback(url):
    html_container = {}

    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        html_container["html"] = loop.run_until_complete(playwright_fetch_async(url))
        loop.close()

    try:
        t = threading.Thread(target=runner, daemon=True)
        t.start()
        t.join(timeout=60)

        html = html_container.get("html")
        if html:
            return BeautifulSoup(html, "lxml")

    except Exception as e:
        print(f"    [PLAYWRIGHT THREAD FAIL] {url} → {e}")

    return None

async def playwright_fetch_async(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        )


        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # STEP 1: wait for ANY meaningful content
        await page.wait_for_function(
            "document.body && document.body.innerText.length > 200",
            timeout=15000
        )

        # STEP 2: extra stabilization wait
        await page.wait_for_timeout(2000)

        # STEP 3: optional JS render flush
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
        except:
            pass

        html = await page.content()
        await browser.close()

        return html
    
def kw_match(text, keywords):
    t = text.lower()
    return any(k in t for k in keywords)

def clean(text, maxlen=500):
    return " ".join(text.split())[:maxlen]

def get_article_body(url, maxchars=600):
    soup = safe_get(url, timeout=12)
    if not soup:
        return ""
    for sel in ["div.story__content", "div.article-body", "div.entry-content",
                "div.post-content", "article", "div.content"]:
        tag_name = sel.split(".")[0]
        cls      = sel.split(".")[1] if "." in sel else None
        el = soup.find(tag_name, class_=cls) if cls else soup.find(tag_name)
        if el:
            paras = [p.get_text(strip=True) for p in el.find_all("p") if len(p.get_text(strip=True)) > 40]
            text  = " ".join(paras)
            return clean(text, maxchars)
    return ""

def scrape_search_results(url, base_url="", limit=8):
    soup = safe_get(url)
    results = []
    seen = set()

    if not soup:
        return results

    for a in soup.find_all("a", href=True):
        title = clean(a.get_text(" ", strip=True), 300)
        href = a.get("href", "").strip()

        if len(title) < 20:
            continue

        if href.startswith("/"):
            href = urljoin(base_url, href)

        if href in seen:
            continue

        seen.add(href)

        results.append({
            "title": title,
            "url": href
        })

        if len(results) >= limit:
            break

    return results

def enrich_articles_with_summary(items, maxchars=500):
    enriched = []
    for item in items:
        title = item.get("title", "")
        url = item.get("url", "")
        summary = get_article_body(url, maxchars) if url else ""
        enriched.append({
            "title": title,
            "url": url,
            "summary": summary
        })
    return enriched

def get_drap_regulatory_updates_2026():
    """
    DRAP regulatory updates listing page.
    Keep only 2026 items.
    """
    url = "https://www.dra.gov.pk/category/news_updates/regulatory_updates/"
    result = {
        "items": [],
        "source": url
    }

    soup = safe_get(url)
    if not soup:
        return result

    articles = soup.find_all("article")
    if articles:
        for article in articles:
            h2 = article.find("h2", class_="entry-title")
            if not h2:
                continue

            a = h2.find("a", href=True)
            if not a:
                continue

            title = clean(a.get_text(" ", strip=True), 300)
            href = a["href"].strip()

            time_tag = article.find("time", class_="entry-date")
            date_text = ""
            if time_tag:
                date_text = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)

            if "2026" not in date_text:
                continue

            result["items"].append({
                "title": title,
                "url": href,
                "date": date_text
            })

    else:
        # fallback
        for h2 in soup.find_all("h2", class_="entry-title"):
            a = h2.find("a", href=True)
            if not a:
                continue

            title = clean(a.get_text(" ", strip=True), 300)
            href = a["href"].strip()

            parent = h2.parent
            date_text = ""
            if parent:
                time_tag = parent.find("time")
                if time_tag:
                    date_text = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)

            if "2026" not in date_text:
                continue

            result["items"].append({
                "title": title,
                "url": href,
                "date": date_text
            })

    return result

def is_recyclingtoday_relevant(title: str) -> bool:
    kws = [
        "manufacturing", "factory", "factories", "pharma", "pharmaceutical",
        "production", "industrial", "plant", "processing", "material",
        "recycling", "plastics", "packaging", "waste", "circular"
    ]
    t = (title or "").lower()
    return any(k in t for k in kws)

def get_recyclingtoday_article_body(url, maxchars=900):
    soup = safe_get(url, timeout=20)
    if not soup:
        return ""

    selectors = [
        ("article", None),
        ("div", "article-body"),
        ("div", "entry-content"),
        ("div", "content"),
        ("main", None),
    ]

    for tag_name, cls in selectors:
        el = soup.find(tag_name, class_=cls) if cls else soup.find(tag_name)
        if not el:
            continue

        paras = []
        for p in el.find_all("p"):
            txt = p.get_text(" ", strip=True)
            if len(txt) > 40 and "Subscribe" not in txt:
                paras.append(txt)

        body = " ".join(paras)
        if body:
            return clean(body, maxchars)

    return ""

def get_recyclingtoday_relevant_articles_2026_playwright():
    base = "https://www.recyclingtoday.com"
    url = f"{base}/news/"
    result = {
        "articles": [],
        "source": url
    }
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)

        for _ in range(8):
            buttons = page.locator("button.load-more")
            if buttons.count() == 0:
                break
            try:
                buttons.first.click()
                page.wait_for_timeout(1500)
            except Exception:
                break

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["h2", "h3"]):
        a = tag.find("a", href=True)
        if not a:
            continue

        title = clean(a.get_text(" ", strip=True), 300)
        href = urljoin(base, a["href"])

        if len(title) < 15 or href in seen:
            continue
        if not is_recyclingtoday_relevant(title):
            continue

        seen.add(href)

        art_soup = safe_get(href, timeout=20)
        if not art_soup:
            continue

        published_text = ""
        for node in art_soup.find_all(["time", "span", "p", "div"], limit=80):
            txt = node.get_text(" ", strip=True)
            if "2026" in txt:
                published_text = txt
                break

        if "2026" not in published_text:
            continue

        summary = get_recyclingtoday_article_body(href, 900)

        result["articles"].append({
            "title": title,
            "url": href,
            "date": published_text,
            "summary": summary
        })

    return result

def get_recyclingtoday_relevant_articles_2026():
    base = "https://www.recyclingtoday.com"
    url = f"{base}/news/"
    result = {"articles": [], "source": url}

    soup = safe_get(url)
    if not soup:
        return result

    seen = set()

    for tag in soup.find_all(["h2", "h3"]):
        a = tag.find("a", href=True)
        if not a:
            continue

        title = clean(a.get_text(" ", strip=True), 300)
        href = urljoin(base, a["href"])

        if len(title) < 15 or href in seen:
            continue
        if not is_recyclingtoday_relevant(title):
            continue

        seen.add(href)

        art_soup = safe_get(href, timeout=20)
        if not art_soup:
            continue

        published_text = ""
        for node in art_soup.find_all(["time", "span", "p", "div"], limit=80):
            txt = node.get_text(" ", strip=True)
            if "2026" in txt:
                published_text = txt
                break

        if "2026" not in published_text:
            continue

        summary = get_recyclingtoday_article_body(href, 900)

        result["articles"].append({
            "title": title,
            "url": href,
            "date": published_text,
            "summary": summary
        })

    return result

def save_current_as_last_week(data):
    """
    Save FULL snapshot of everything scraped so we can:
    - debug extraction
    - compare weekly changes
    - inspect missing data
    """
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    snapshot = {
        "saved_at": datetime.now().isoformat(),
        "generated_at": data.get("generated_at"),
        "week_label": data.get("week_label"),

        # FULL RAW DATA (this is the key change)
        "full_snapshot": data,

        # optional quick-access summaries
        "summary_counts": {
            "forex": len(data.get("economic", {}).get("forex", {}).get("open_market", {})),
            "fuel": len(data.get("economic", {}).get("fuel", {}).get("prices", [])),
            "commodities_energy": len(data.get("economic", {}).get("commodities", {}).get("energy", [])),
            "commodities_metals": len(data.get("economic", {}).get("commodities", {}).get("metals", [])),
            "sbp": len(data.get("economic", {}).get("inflation", {}).get("sbp_highlights", [])),
            "fbr": len(data.get("economic", {}).get("inflation", {}).get("fbr_sros", [])),
            "brecorder": len(data.get("economic", {}).get("inflation", {}).get("brecorder_econ", [])),
            "dawn": len(data.get("economic", {}).get("inflation", {}).get("dawn_pakistan", [])),
            "pwc_dev": len(data.get("economic", {}).get("pwc_developments", {}).get("content", "")),
            "pwc_tax_rows": len(data.get("economic", {}).get("pwc_corporate_tax", [])),
            "pharma_tech": len(data.get("pharma_tech", {}).get("articles", [])),
            "global_articles": len(data.get("economic", {}).get("global", {}).get("articles", [])),
        }
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

def load_last_week():
    """
    Loads last week's snapshot.
    Returns empty dict if file does not exist or is empty/corrupt.
    """
    if not os.path.exists(DATA_FILE):
        return {}

    if os.path.getsize(DATA_FILE) == 0:
        # File exists but is empty
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Corrupt or partially written file
        return {}

def latest_business_day(base_date=None):
    """
    Return the latest weekday date.
    Sat -> Fri
    Sun -> Fri
    Mon-Fri -> same day
    """
    d = base_date or datetime.now()

    while d.weekday() >= 5:   # 5=Sat, 6=Sun
        d -= timedelta(days=1)

    return d


def business_day_str(fmt="%Y-%m-%d", base_date=None):
    return latest_business_day(base_date).strftime(fmt)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — ECONOMIC CONDITIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_forex():
    """forex.pk — open market rates + NBP PDF interbank rates"""
    result = {"open_market": {}, "nbp": {}, "sources": []}

    # A) forex.pk open market
    soup = safe_get("https://www.forex.pk/open_market_rates.asp")
    if soup:
        cmap = {
            "us dollar":     "USD", "euro":          "EUR",
            "UK Pound Sterling": "GBP", "china yuan":  "CNY",
            "saudi riyal":   "SAR", "u.a.e dirham":    "AED",
            "indian rupee":  "INR", "afghan afghani":"AFN",
        }
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[0].get_text(strip=True).lower()
                buy  = cells[2].get_text(strip=True)
                sell = cells[3].get_text(strip=True)
                for label, code in cmap.items():
                    if label in name:
                        result["open_market"][code] = {"buy": buy, "sell": sell}
        if result["open_market"]:
            result["sources"].append("https://www.forex.pk/open_market_rates.asp")

    # B) NBP rate sheet PDF — dynamic daily URL
    start_date = latest_business_day()
    for delta in range(5):
        d = start_date - timedelta(days=delta)
            # skip weekends while walking backward
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        url = f"https://www.nbp.com.pk/RateSheetFiles/NBP-RateSheet-{d.strftime('%d-%m-%Y')}.pdf"
        resp = safe_get(url, raw=True)
        if resp and resp.status_code == 200:
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(resp.content))
                text = "\n".join(p.extract_text() or "" for p in reader.pages)
                for code in ["USD", "EUR", "GBP", "SAR", "AED", "CNY"]:
                    m = re.search(
                        rf"\b{code}\b.*?(\d{{2,4}}\.?\d{{0,4}})\s+(\d{{2,4}}\.?\d{{0,4}})",
                        text, re.IGNORECASE)
                    if m:
                        result["nbp"][code] = {"buy": m.group(1), "sell": m.group(2)}
                if result["nbp"]:
                    result["sources"].append(url)
                    break
            except:
                pass
    return result

def get_fuel():
    """
    Pakistan fuel prices from PakWheels:
    - Current price
    - Previous price
    - Difference
    """
    url = "https://www.pakwheels.com/petroleum-prices-in-pakistan"
    result = {
        "prices": [],
        "source": url
    }

    soup = safe_get(url)
    if not soup:
        return result

    container = soup.find("div", class_="pricing-table-cont")
    if not container:
        return result

    table = container.find("table")
    if not table:
        return result

    tbody = table.find("tbody")
    if not tbody:
        return result

    for row in tbody.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        product = cols[0].get_text(strip=True)

        old_txt = cols[1].get_text(strip=True)
        new_txt = cols[2].get_text(strip=True)
        diff_txt = cols[3].get_text(strip=True)

        # Extract numeric values
        try:
            old_val = float(re.search(r"[\d.]+", old_txt).group())
            new_val = float(re.search(r"[\d.]+", new_txt).group())
            diff_val = float(re.search(r"[\d.]+", diff_txt).group())
        except:
            continue

        # Detect direction (up / down)
        if "caret-down" in str(cols[3]):
            diff_val = -abs(diff_val)
        elif "caret-up" in str(cols[3]):
            diff_val = abs(diff_val)

        result["prices"].append({
            "product":  product,
            "price":    new_txt,
            "value":    new_val,
            "previous": old_val,
            "change":   diff_val
        })

    return result


def get_commodities_table():
    soup = safe_get("https://tradingeconomics.com/commodities")
    result = {"energy": [], "metals": []}

    if not soup:
        return result

    energy_targets = ["crude oil", "natural gas", "coal", "methanol"]
    metal_targets  = ["gold", "silver", "copper", "iron ore", "steel", "platinum"]

    def match_target(name, targets):
        n = name.lower()
        return any(t in n for t in targets)

    tables = soup.find_all("table", class_="table-heatmap")

    for table in tables:
        # Detect section (Energy / Metals)
        header = table.find("th", class_="te-sort")
        if not header:
            continue

        section = header.get_text(strip=True).lower()

        if "energy" in section:
            section_key = "energy"
            targets = energy_targets
        elif "metal" in section:
            section_key = "metals"
            targets = metal_targets
        else:
            continue

        tbody = table.find("tbody")
        if not tbody:
            continue

        for row in tbody.find_all("tr"):
            first = row.find("td", class_="datatable-item-first")
            if not first:
                continue

            # Commodity name
            b = first.find("b")
            name = b.get_text(strip=True) if b else ""
            if not name or not match_target(name, targets):
                continue

            # Unit (USD/Bbl, USD/t.oz, etc.)
            unit_tag = first.find("div")
            unit = unit_tag.get_text(strip=True) if unit_tag else ""

            # Price (row‑scoped ID is safe)
            price_tag = row.find("td", id="p")
            price = price_tag.get_text(strip=True) if price_tag else ""

            # Weekly change (first heatmap cell = Weekly)
            weekly = ""
            heatmap_cells = row.find_all("td", class_="datatable-heatmap")
            if heatmap_cells:
                weekly = heatmap_cells[0].get_text(strip=True)

            result[section_key].append({
                "name": name,
                "unit": unit,
                "price": price,
                "weekly": weekly
            })

    print(
        "Commodities fetched →",
        "Energy:", len(result["energy"]),
        "Metals:", len(result["metals"])
    )

    return result

def get_drap_bans():
    """DRAP banned/restricted products"""
    result = {"items": [], "source": "https://www.dra.gov.pk/"}
    soup = safe_get("https://www.dra.gov.pk/")
    if soup:
        kws = ["ban", "banned", "suspend", "recall", "restrict", "prohibit",
               "substandard", "spurious", "counterfeit"]
        for tag in soup.find_all(["a","li","p","h3"], limit=100):
            txt = tag.get_text(strip=True)
            if kw_match(txt, kws) and 15 < len(txt) < 250:
                result["items"].append(txt)
        result["items"] = list(dict.fromkeys(result["items"]))[:8]
    # Also check DRAP alerts page
    soup2 = safe_get("https://www.dra.gov.pk/en/publichealth/drug-alerts")
    if soup2:
        for tag in soup2.find_all(["a","li","td"], limit=60):
            txt = tag.get_text(strip=True)
            if len(txt) > 20:
                result["items"].append(txt)
        result["items"] = list(dict.fromkeys(result["items"]))[:10]
    return result

def get_inflation_taxes():
    """SBP inflation + FBR new duties/taxes + BRecorder economy + PwC corporate tax data"""

    result = {
        "sbp_highlights":  [],
        "fbr_sros":        [],
        "brecorder_econ":  [],
        "dawn_pakistan":   [],
        "pwc_developments": {},
        "pwc_corporate_tax": [],
        "sources":         []
    }

    # ─────────────────────────────────────────
    # SBP
    # ─────────────────────────────────────────
    soup = safe_get("https://www.sbp.org.pk/")
    if soup:
        kws = ["policy rate","inflation","cpi","monetary","mpc","interest","bps","percent"]
        for tag in soup.find_all(["p","li","a","span"], limit=100):
            txt = tag.get_text(strip=True)
            if kw_match(txt, kws) and 20 < len(txt) < 280:
                result["sbp_highlights"].append(txt)

        result["sbp_highlights"] = list(dict.fromkeys(result["sbp_highlights"]))[:5]
        result["sources"].append("https://www.sbp.org.pk/")

    # ─────────────────────────────────────────
    # FBR
    # ─────────────────────────────────────────
    soup2 = safe_get("https://www.fbr.gov.pk/")
    if soup2:
        for tag in soup2.find_all(["a","li"], limit=100):
            txt = tag.get_text(strip=True)
            if re.search(r"S\.?R\.?O", txt) and len(txt) > 15:
                result["fbr_sros"].append(txt[:200])

        result["fbr_sros"] = list(dict.fromkeys(result["fbr_sros"]))[:6]
        result["sources"].append("https://www.fbr.gov.pk/")

    # ─────────────────────────────────────────
    # BRecorder Economy
    # ─────────────────────────────────────────
    today = datetime.now().strftime("%Y-%m-%d")
    soup3 = safe_get(f"https://www.brecorder.com/business-finance/{today}")

    if soup3:
        kws2 = ["tax","duty","tariff","inflation","import","export","customs",
                "fbr","sbp","economic","trade","rupee","dollar"]

        for a in soup3.find_all("a", class_=lambda c: c and "story__link" in c):
            title = a.get_text(strip=True)
            href  = a.get("href","")

            if kw_match(title, kws2) and len(title) > 20:
                if href.startswith("/"):
                    href = "https://www.brecorder.com" + href

                summary = get_article_body(href, 400)

                result["brecorder_econ"].append({
                    "title": title,
                    "url": href,
                    "summary": summary
                })

        result["sources"].append(f"https://www.brecorder.com/business-finance/{today}")

    # ─────────────────────────────────────────
    # Dawn Business
    # ─────────────────────────────────────────
    soup4 = safe_get("https://www.dawn.com/pakistan")

    
    if soup4:
        kws3 = [
            "tax","duty","trade","economy","inflation","import",
            "export","rupee","power","electricity","gas",
            "solar","loadshedding","S.I.T.E","deposit","trade"
            "ban","credit","imf","loan"
        ]
    
        for a in soup4.find_all("a", class_="story__link", limit=20):
            title = a.get_text(strip=True)
    
            # ✅ KEYWORD FILTER (CRITICAL)
            if not kw_match(title, kws3) or len(title) < 20:
                continue
    
            url = a.get("href", "")
            if not url.startswith("http"):
                url = "https://www.dawn.com" + url
    
            article_div = a.find_parent("div")
    
            summary = ""
            last_updated = ""
    
            if article_div:
                # Extract summary
                excerpt = article_div.find("div", class_="story__excerpt")
                if excerpt:
                    summary = excerpt.get_text(strip=True)
    
                # Extract updated timestamp
                time_span = article_div.find("span", class_="timestamp--time")
                if time_span:
                    last_updated = time_span.get("title", "").strip()
    
            result["dawn_pakistan"].append({
                "title": title,
                "url": url,
                "summary": summary,
                "last_updated": last_updated
            })
    
        # De-duplicate by title
        result["dawn_pakistan"] = list(
            {item["title"]: item for item in result["dawn_pakistan"]}.values()
        )[:5]
    
        result["sources"].append("https://www.dawn.com/pakistan")


    # ─────────────────────────────────────────
    # 🆕 PwC Significant Developments
    # ─────────────────────────────────────────
    try:
        pwc_dev = get_pwc_significant_developments()
        result["pwc_developments"] = pwc_dev

        if pwc_dev.get("last_reviewed"):
            result["sources"].append(
                "https://taxsummaries.pwc.com/pakistan/corporate/significant-developments"
            )
    except Exception as e:
        print(f"    [WARN] PwC developments failed → {e}")

    # ─────────────────────────────────────────
    # 🆕 PwC Corporate Tax Rates
    # ─────────────────────────────────────────
    try:
        pwc_tax = get_pwc_corporate_tax_rates()
        result["pwc_corporate_tax"] = pwc_tax

        if pwc_tax:
            result["sources"].append(
                "https://taxsummaries.pwc.com/pakistan/corporate/taxes-on-corporate-income"
            )
    except Exception as e:
        print(f"    [WARN] PwC tax table failed → {e}")

    return result

# ==========================================================
#                 taxes
# ==========================================================


def get_pwc_significant_developments():
    url = "https://taxsummaries.pwc.com/pakistan/corporate/significant-developments"
    soup = safe_get(url)

    if not soup:
        return {}

    # Header
    header = soup.find("header", class_="heading-grp")

    title = ""
    last_reviewed = ""

    if header:
        h2 = header.find("h2", class_="section__heading")
        if h2:
            title = h2.get_text(strip=True)

        span = header.find("span", id="lastReviewedDate")
        if span:
            last_reviewed = span.get_text(strip=True)

    # Full body
    body_div = soup.find("div", id="txtPageBody")
    full_text = ""

    if body_div:
        full_text = " ".join(body_div.stripped_strings)

    return {
        "title": title,
        "last_reviewed": last_reviewed,
        "content": full_text
    }

def get_pwc_corporate_tax_rates():
    url = "https://taxsummaries.pwc.com/pakistan/corporate/taxes-on-corporate-income"
    soup = safe_get(url)

    if not soup:
        return []

    result = []

    # Find table body
    table = soup.find("tbody")
    if not table:
        return result

    rows = table.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) != 2:
            continue

        company_type = cols[0].get_text(" ", strip=True)
        tax_rate = cols[1].get_text(" ", strip=True)

        # Skip header row
        if "company type" in company_type.lower():
            continue

        result.append({
            "company_type": company_type,
            "tax_rate": tax_rate
        })

    return result

def get_global_economic():
    """Global economic context: China, USA, Europe, Middle East, India, Afghanistan"""
    result = {"articles": [], "sources": []}
    today = datetime.now().strftime("%Y-%m-%d")

    # BRecorder world economy
    soup = safe_get("https://www.brecorder.com/business-finance")
    if soup:
        kws = ["china","usa","america","europe","middle east","india","afghanistan",
               "global","inflation","trade war","tariff","oil","supply chain",
               "imf","world bank","fed","federal reserve"]
        for a in soup.find_all("a", class_=lambda c: c and "story__link" in c, limit=40):
            title = a.get_text(strip=True)
            href  = a.get("href","")
            if kw_match(title, kws) and len(title) > 20:
                if href.startswith("/"):
                    href = "https://www.brecorder.com" + href
                summary = get_article_body(href, 400)
                result["articles"].append({"title": title, "url": href,
                                           "summary": summary, "region": _detect_region(title)})
                if len(result["articles"]) >= 8:
                    break
        result["sources"].append("https://www.brecorder.com/business-finance")

    # Dawn World
    soup2 = safe_get("https://www.dawn.com/business")
    if soup2:
        kws2 = ["economy","trade","inflation","oil","supply","china","us","europe","india"]
        for tag in soup2.find_all(["h2","h3"], limit=30):
            a = tag.find("a")
            if a:
                txt = a.get_text(strip=True)
                href = a.get("href","")
                if kw_match(txt, kws2) and len(txt) > 20:
                    if href.startswith("/"):
                        href = "https://www.dawn.com" + href
                    result["articles"].append({"title": txt, "url": href,
                                               "summary": "", "region": _detect_region(txt)})
        result["sources"].append("https://www.dawn.com/world")


    return result

def _detect_region(text):
    t = text.lower()
    for r, kws in [
        ("China",       ["china","chinese","beijing","shanghai"]),
        ("USA",         ["usa","us ","united states","american","fed ","trump","biden"]),
        ("Europe",      ["europe","european","eu ","ecb","euro zone"]),
        ("Middle East", ["middle east","gulf","saudi","uae","iran","israel","opec"]),
        ("India",       ["india","indian","modi","delhi","mumbai"]),
        ("Afghanistan", ["afghanistan","afghan","kabul","taliban"]),
        ("Pakistan",    ["pakistan","karachi","lahore","islamabad","islamabad","sbp","fbr"]),
    ]:
        if any(k in t for k in kws):
            return r
    return "Global"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — TECHNOLOGY IN PHARMA
# ─────────────────────────────────────────────────────────────────────────────

def get_pharma_tech():
    """
    Pharma technology, innovation, AI, automation, biotech
    Pakistan + Global
    """
    result = {
        "articles": [],
        "research": [],
        "sources": []
    }

    pharma_kws = [
        "pharma", "pharmaceutical", "technology", "automation", "ai",
        "artificial intelligence", "digital", "manufacturing", "blockchain",
        "research", "drug", "clinical", "biotech", "health","Product development","sampling"
        "production","vaccine","virus","cancer"
    ]

    # ─────────────────────────────────────────
    # 1. Dawn – Pharma / Tech Search
    # ─────────────────────────────────────────
    dawn_tech_search_urls = [
        "https://www.dawn.com/search?cx=016184311056644083324%3Aa1i8yd7zymy&ie=UTF-8&q=pharma+technology",
        "https://www.dawn.com/search?cx=016184311056644083324%3Aa1i8yd7zymy&ie=UTF-8&q=pharmaceutical",
    ]
    print("Fetching Dawn NEWS Articles")


    for url in dawn_tech_search_urls:
        try:
            items = scrape_search_results(url, base_url="https://www.dawn.com", limit=6)
            items = [x for x in items if kw_match(x.get("title",""), pharma_kws)]
            enriched = enrich_articles_with_summary(items, maxchars=450)

            for art in enriched:
                art["source"] = "Dawn"
                art["country"] = "Pakistan"
                result["articles"].append(art)

            result["sources"].append("https://www.dawn.com")
        except Exception as e:
            print(f"[WARN] Dawn pharma-tech failed → {e}")

    # ─────────────────────────────────────────
    # 2. ARY News – Health Category (Pakistan)
    # ─────────────────────────────────────────
    try:
        soup = safe_get("https://arynews.tv/category/health-2")
    
        # 🔴 fallback to Playwright if content looks small
        if soup and len(soup.text) < 20000:
            print("[INFO] ARY page incomplete → using Playwright")
            soup = playwright_fallback("https://arynews.tv/category/health-2")
    
        if soup:
            seen = set()
    
            boxes = soup.select("div.col-md-4.col-p article")
    
            print(f"[DEBUG] ARY articles found: {len(boxes)}")
    
            for box in boxes:   # ❌ removed [:12] limit
    
                # ✅ strictly get title link
                a = box.select_one("h3 a")
                if not a:
                    continue
    
                title = a.get_text(strip=True)
                url = a.get("href", "").strip()
    
                if not title or not url:
                    continue
    
                if url in seen:
                    continue
                seen.add(url)
    
                # ✅ date extraction
                date_tag = box.select_one("ul.authar-info li")
                date = date_tag.get_text(strip=True) if date_tag else ""
    
                result["articles"].append({
                    "title": title,
                    "url": url,
                    "summary": "",
                    "date": date,
                    "source": "ARY News",
                    "country": "Pakistan"
                })
    
            result["sources"].append("https://arynews.tv/category/health-2")
    
    except Exception as e:
        print(f"[WARN] ARY News failed → {e}")
    # ─────────────────────────────────────────
    # 3. ISPE – Future Pharma Trends (Global)
    # ─────────────────────────────────────────
    try:
        soup = safe_get(
            "https://ispe.org/pharmaceutical-engineering/ispeak/top-five-future-trends-pharmaceutical-industry-2026"
        )
        if soup:
            print("Fetching ISPE NEWS Articles")

            for h3 in soup.find_all("h3"):
                title = h3.get_text(strip=True)
                if not kw_match(title, pharma_kws):
                    continue

                summary_parts = []
                
                for p in h3.find_next_siblings("p", limit=2):
                    txt = p.get_text(" ", strip=True)
                    if len(txt) > 40:
                        summary_parts.append(txt)

                summary = " ".join(summary_parts)

                result["articles"].append({
                    "title": title,
                    "url": "https://ispe.org/pharmaceutical-engineering/ispeak/top-five-future-trends-pharmaceutical-industry-2026",
                    "summary": summary[:500],
                    "source": "ISPE",
                    "country": "Global"
                })

            result["sources"].append("ISPE")
    except Exception as e:
        print(f"[WARN] ISPE failed → {e}")

    # ─────────────────────────────────────────
    # 4. Fast Company – Innovative Pharma (Global)
    # ─────────────────────────────────────────
    try:
        soup = safe_get(
            "https://www.fastcompany.com/91497260/medicines-therapeutics-pharmaceuticals-most-innovative-companies-2026"
        )
        if soup:
            for h2 in soup.find_all("h2", class_="wp-block-heading"):
                title = h2.get_text(strip=True)
                p = h2.find_next("p")
                if not p:
                    continue

                summary = p.get_text(" ", strip=True)
                if len(summary) < 30:
                    continue

                result["articles"].append({
                    "title": title,
                    "url": "https://www.fastcompany.com/91497260/medicines-therapeutics-pharmaceuticals-most-innovative-companies-2026",
                    "summary": summary,
                    "source": "Fast Company",
                    "country": "Global"
                })

            result["sources"].append("Fast Company")
    except Exception as e:
        print(f"[WARN] Fast Company failed → {e}")

    # ─────────────────────────────────────────
    # 5. Epicflow – Pharma Technology Trends
    # ─────────────────────────────────────────

    try:
        url = "https://www.epicflow.com/blog/top-trends-in-the-pharmaceutical-industry-what-to-expect/"
        soup = safe_get(url)
    
        if not soup:
            print("[WARN] Failed to fetch page")
            return result
    
        print("Fetching EpicFlow Trends")
    
        # STEP 1: get ALL h3 trends directly
        headings = soup.select("div.et_pb_text_inner h3")
    
        for h3 in headings:
    
            # clean title
            title = " ".join(h3.stripped_strings)
            title = re.sub(r"^\d+\.\s*", "", title).strip().rstrip(".")
    
            content_blocks = []
    
            # STEP 2: collect content until next h3 (global traversal)
            for sibling in h3.find_next_siblings():
                if sibling.name == "h3":
                    break
    
                if sibling.name == "p":
                    text = sibling.get_text(" ", strip=True)
                    if text:
                        content_blocks.append(text)
    
                elif sibling.name == "ul":
                    for li in sibling.find_all("li"):
                        li_text = li.get_text(" ", strip=True)
                        if li_text:
                            content_blocks.append("- " + li_text)
    
            summary = " ".join(content_blocks)
    
            result["articles"].append({
                "title": title,
                "url": url,
                "summary": summary[:600],
                "source": "Epicflow",
                "country": "Global"
            })
    
        result["sources"].append("Epicflow")
    
    except Exception as e:
        print(f"[WARN] Epicflow failed → {e}")
    # ─────────────────────────────────────────
    # 6. Atradius – Country-Level Pharma Outlook
    # ─────────────────────────────────────────
    # try:
    #     soup = safe_get(
    #         "https://atradiuscollections.com/us/knowledge-and-research/reports/industry-trends-pharmaceuticals-january-2026"
    #     )
    #     container = soup.find("div", class_="textModule") if soup else None

    #     current_country = None
    #     current_title = None

    #     if container:
    #         for tag in container.find_all(["h2", "h3", "p"]):
    #             if tag.name == "h2":
    #                 current_country = tag.get_text(strip=True)

    #             elif tag.name == "h3":
    #                 current_title = tag.get_text(strip=True)

    #             elif tag.name == "p" and current_country and current_title:
    #                 summary = tag.get_text(" ", strip=True)
    #                 if len(summary) > 60:
    #                     result["articles"].append({
    #                         "title": current_title,
    #                         "summary": summary[:500],
    #                         "url": "https://atradiuscollections.com/us/knowledge-and-research/reports/industry-trends-pharmaceuticals-january-2026",
    #                         "source": "Atradius",
    #                         "country": current_country
    #                     })

    #         result["sources"].append("Atradius")
    # except Exception as e:
    #     print(f"[WARN] Atradius failed → {e}")

    # ─────────────────────────────────────────
    # 7. Google Scholar – Research (Optional)
    # ─────────────────────────────────────────
    for q in [
        "pharmaceutical AI manufacturing 2026",
        "pharmaceutical supply chain 2026",
        "Drug sampling 2026",
        "vaccine 2026",
        "medicine 2026",
        "Treatment 2026",
        "cancer 2026",
        "Production in pharma 2026",
        "Pharma IOT 2026",
        "Clinical Trials 2026",

        "pharmaceutical AI manufacturing 2025",
        "pharmaceutical supply chain 2025",
        "Drug sampling 2025",
        "vaccine 2025",
        "medicine 2025",
        "Treatment 2025",
        "cancer 2025",
        "Production in pharma 2025",
        "Pharma IOT 2025",
        "Clinical Trials 2025"
        
    ]:
        try:
            gs_url = f"https://scholar.google.com/scholar?q={q}&as_ylo=2023"
            soup = safe_get(gs_url)
            if soup:
                for h3 in soup.select("h3.gs_rt a")[:3]:
                    result["research"].append({
                        "title": h3.get_text(strip=True),
                        "url": h3.get("href", ""),
                        "source": "Google Scholar"
                    })
        except:
            pass

    # ─────────────────────────────────────────
    # Final Deduplication
    # ─────────────────────────────────────────
    seen = set()
    deduped = []

    for art in result["articles"]:
        key = (
            art.get("title", "").lower().strip(),
            art.get("url", "").lower().strip()
        )
        if key not in seen:
            seen.add(key)
            deduped.append(art)

    result["articles"] = deduped[:50]
    return result

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — NEW PRODUCT LAUNCHES & DISEASE TRENDS
# ─────────────────────────────────────────────────────────────────────────────

def get_new_products():
    """New drug launches, pipeline, disease trends, most-demanded medicines"""
    result = {
        "launches": [],
        "pipeline": [],
        "disease_trends": [],
        "drap_approvals": [],
        "sources": []
    }

    
    # -----------------------------
    # 1. PHARMAPHORUM (Drugs to Watch 2026)
    # -----------------------------
    try:
        url1 = "https://pharmaphorum.com/news/11-high-impact-drugs-look-out-2026"
        soup1 = safe_get(url1)
     
        if soup1:
            print("Fetching Pharmaphorum Drugs")
            print("Soup1 exists:", bool(soup1))
     
            container = soup1.find("div", class_="field--name-field-body")
     
            if container:
                drugs = []
     
                for tag in container.find_all("strong"):
                    text = tag.get_text(" ", strip=True)
     
                    # match "1) DrugName"
                    match = re.match(r"^\d+\)\s*(.+)", text)
     
                    if match:
                        drug_name = match.group(1).strip()
     
                        drugs.append({
                            "type": "drug_to_watch_2026",
                            "drug": drug_name,
                            "source": url1
                        })
     
                result["launches"].extend(drugs[:11])
                result["sources"].append(url1)
     
            else:
                print("[WARN] Pharmaphorum container not found")
     
        else:
            print("[WARN] Pharmaphorum fetch failed")
     
    except Exception as e:
        print(f"[WARN] Pharmaphorum failed → {e}")
     
    # -----------------------------
    # 2. DRUGDISCOVERYTRENDS TABLE (Top 10 FY2025)
    # -----------------------------
    try:
        url2 = "https://www.drugdiscoverytrends.com/pharma-50-the-50-best-selling-drugs-of-fy2025/"
        soup2 = safe_get(url2)
     
        if soup2:
            print("Fetching Top FY2025 Drugs Table")
            print("Soup1 exists:", bool(soup1))
            print("Soup2 exists:", bool(soup2))
            print(soup2.prettify()[:1000])
     
            table = soup2.find("table")
     
            if table:
                rows = table.find_all("tr")
     
                top10 = []
     
                for row in rows[1:]:
                    cols = [c.get_text(strip=True) for c in row.find_all("td")]
                
                    if len(cols) < 4:
                        continue
                
                    # skip header accidentally included
                    if cols[0].lower() == "rank":
                        continue
                
                    rank = cols[0]
                    drug = cols[1]
                    manufacturer = cols[2]
                    fy2025 = cols[3]
                
                    top10.append({
                        "type": "top_selling_2025",
                        "rank": rank,
                        "drug": drug,
                        "manufacturer": manufacturer,
                        "fy2025": fy2025,
                        "source": url2
                    })
                
                    if len(top10) == 10:
                        break
     
                result["launches"].extend(top10)
                result["sources"].append(url2)
     
            else:
                print("[WARN] No table found on DrugDiscoveryTrends")
     
        else:
            print("[WARN] DrugDiscoveryTrends fetch failed")
     
    except Exception as e:
        print(f"[WARN] Drug table failed → {e}")
        
    # -----------------------------
    # 3. NATURE RESEARCH (April 2026 only)
    # -----------------------------
    try:
        print("Fetching Nature Research Articles")
    
        collected = []
    
        for page in range(1, 6):
    
            url = (
                "https://www.nature.com/search?"
                "article_type=research%2C+reviews&"
                "subject=cancer%2C+chemical-biology%2C+drug-discovery%2C+molecular-biology&"
                "order=date_desc"
                f"&page={page}"
            )
    
            soup = safe_get(url)
            if not soup:
                continue
    
            articles = soup.find_all("article")
    
            if not articles:
                continue
    
            for art in articles:
    
                # --- TITLE + LINK ---
                h3 = art.find("h3")
                if not h3:
                    continue
    
                a = h3.find("a")
                if not a:
                    continue
    
                title = a.get_text(strip=True)
                link = "https://www.nature.com" + a.get("href", "")
    
                # --- DATE ---
                time_tag = art.find("time")
                if not time_tag:
                    continue
    
                date = time_tag.get("datetime", "")
    
                # ✅ FILTER → April 2026 only
                if not date.startswith("2026-04"):
                    continue
    
                # --- ARTICLE TYPE ---
                type_tag = art.find("span", class_="c-meta__type")
                article_type = type_tag.get_text(strip=True) if type_tag else ""
    
                # --- JOURNAL ---
                journal_tag = art.find("div", {"data-test": "journal-title-and-link"})
                journal = journal_tag.get_text(strip=True) if journal_tag else ""
    
                # --- SUMMARY (NEW FIX) ---
                summary_tag = art.find("div", {"data-test": "article-description"})
                if summary_tag:
                    summary = summary_tag.get_text(" ", strip=True)
                else:
                    summary = title[:300]  # fallback
    
                collected.append({
                    "type": "research_article",
                    "title": title,
                    "summary": summary[:500],
                    "date": date,
                    "article_type": article_type,
                    "journal": journal,
                    "url": link
                })
    
            last_date_tag = articles[-1].find("time")
            if last_date_tag:
                last_date = last_date_tag.get("datetime", "")
                if not last_date.startswith("2026-04"):
                    break
    
        print("Nature articles extracted:", len(collected))
    
        result["pipeline"].extend(collected[:50])
        result["sources"].append("nature.com")
    
    except Exception as e:
        print(f"[WARN] Nature scraping failed → {e}")
     

    return result

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — TECHNOLOGY OVERALL
# ─────────────────────────────────────────────────────────────────────────────

def get_general_tech():
    """New tech in market, manufacturing, recycling, industry applications"""
    result = {
        "emerging_tech": [],
        "manufacturing": [],
        "recycling": [],
        "sources": []
    }

    # BRecorder tech news
    today = business_day_str("%Y-%m-%d")
    soup = safe_get(f"https://www.brecorder.com/technology/{today}")
    if not soup:
        soup = safe_get("https://www.brecorder.com/technology")

    if soup:
        kws = ["ai","artificial intelligence","robotics","iot","blockchain",
               "automation","machine learning","cloud","5g","ev","electric",
               "renewable","manufacturing","recycling","sustainability"]
        for a in soup.find_all("a", class_=lambda c: c and "story__link" in c, limit=30):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if kw_match(title, kws) and len(title) > 20:
                if href.startswith("/"):
                    href = "https://www.brecorder.com" + href
                summary = get_article_body(href, 400)
                result["emerging_tech"].append({"title": title, "url": href, "summary": summary})
        result["sources"].append("https://www.brecorder.com/technology")

    # MIT Technology Review
    soup2 = safe_get("https://www.technologyreview.com/")
    if soup2:
        kws2 = ["manufacturing","pharma","industry","robot","ai","automat",
                "3d print","sensor","iot","supply","recycl","sustainab"]
        for tag in soup2.find_all(["h2","h3"], limit=25):
            a = tag.find("a")
            if a:
                txt = a.get_text(strip=True)
                href = a.get("href", "")
                if kw_match(txt, kws2) and len(txt) > 20:
                    if href.startswith("/"):
                        href = "https://www.technologyreview.com" + href
                    result["manufacturing"].append({"title": txt, "url": href})
        result["sources"].append("https://www.technologyreview.com/")

    # IndustryWeek
    soup3 = safe_get("https://www.industryweek.com/technology-and-iiot")
    if soup3:
        kws3 = ["manufacturing","recycling","sustainability","automation",
                "robot","ai","smart factory","green","circular"]
        for tag in soup3.find_all(["h2","h3"], limit=20):
            a = tag.find("a")
            if a:
                txt = a.get_text(strip=True)
                href = a.get("href", "")
                if kw_match(txt, kws3) and len(txt) > 20:
                    if href.startswith("/"):
                        href = "https://www.industryweek.com" + href
                    cat = "recycling" if kw_match(txt, ["recycl","circular","green","waste","sustainab"]) else "manufacturing"
                    result[cat].append({"title": txt, "url": href})
        result["sources"].append("https://www.industryweek.com/technology-and-iiot")

    # Recycling Today
    try:
        rt = get_recyclingtoday_relevant_articles_2026_playwright()
    except Exception as e:
        print(f"    [WARN] Recycling Today Playwright failed → {e}")
        try:
            rt = get_recyclingtoday_relevant_articles_2026()
        except Exception as e2:
            print(f"    [WARN] Recycling Today fallback failed → {e2}")
            rt = {"articles": [], "source": "https://www.recyclingtoday.com/news/"}

    if rt.get("articles"):
        result["recycling"].extend(rt["articles"])

    if rt.get("source"):
        result["sources"].append(rt["source"])

    return result



# ─────────────────────────────────────────────────────────────────────────────
# MASTER COLLECTOR
# ─────────────────────────────────────────────────────────────────────────────

def collect_all():
    print("=" * 60)
    print("  WEEKLY PHARMA INTELLIGENCE — DATA COLLECTION")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %I:%M %p')}")
    print("=" * 60)

    last_week = load_last_week()

    print("\n[1/8] Forex rates (forex.pk + NBP PDF)...")
    forex = get_forex()

    print("\n[2/8] Fuel prices (psopk.com)...")
    fuel  = get_fuel()

    print("\n[3/8] Commodity prices (steel/copper/aluminium)...")
    commodities = get_commodities_table()

    print("\n[4/8] Inflation, taxes + PwC data...")
    inflation = get_inflation_taxes()

    # 👇 extract PwC separately for report clarity (optional but useful)
    pwc_development = inflation.get("pwc_developments", {})
    pwc_tax_table   = inflation.get("pwc_corporate_tax", [])

    print("\n[4.5/8] Global economic context...")
    global_eco = get_global_economic()

    print("\n[5/8] DRAP regulatory updates (2026)...")
    drap_updates = get_drap_regulatory_updates_2026()

    print("\n[6/8] Technology in Pharma (research + articles)...")
    pharma_tech = get_pharma_tech()

    print("\n[7/8] New product launches + disease trends...")
    new_products = get_new_products()

    print("\n[8/8] General technology (manufacturing + recycling)...")
    gen_tech = get_general_tech()

    data = {
        "generated_at": datetime.now().strftime("%A, %d %B %Y — %I:%M %p"),
        "week_label":   _week_label(),
        "date_short":   datetime.now().strftime("%Y-%m-%d"),
        "last_week":    last_week,
        "economic": {
            "forex": forex,
            "fuel": fuel,
            "commodities": commodities,
            "inflation": inflation,
            "pwc_developments": pwc_development,
            "pwc_corporate_tax": pwc_tax_table,
            "global": global_eco,
            "drap_updates": drap_updates,
        },
        "pharma_tech":   pharma_tech,
        "new_products":  new_products,
        # "gen_tech":      gen_tech,
    }

    # Collect ALL references across all sections
    data["all_references"] = _collect_all_refs(data)

    # Save snapshot for next week's comparison
    save_current_as_last_week(data)

    print(f"\nDone. {len(data['all_references'])} unique sources collected.\n")
    return data


def _week_label():
    now   = datetime.now()
    start = now - timedelta(days=now.weekday())
    end   = start + timedelta(days=6)
    return f"{start.strftime('%d %b')} – {end.strftime('%d %b %Y')}"


def _collect_all_refs(data):
    """Walk entire data tree and collect every URL."""
    refs = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("url", "source") and isinstance(v, str) and v.startswith("http"):
                    refs.add(v)
                elif k == "sources" and isinstance(v, list):
                    for s in v:
                        if isinstance(s, str) and s.startswith("http"):
                            refs.add(s)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return sorted(refs)


if __name__ == "__main__":
    import json
    d = collect_all()
    print(json.dumps({"refs": d["all_references"][:10]}, indent=2))
    print("get_general_tech exists:", callable(get_general_tech))
