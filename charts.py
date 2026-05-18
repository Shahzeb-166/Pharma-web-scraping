"""
charts.py — Generate comparison charts as PNG images for the weekly report.
Primary colour: #039fe2  |  Font: Times New Roman (falls back to serif)
"""

import os
import matplotlib
matplotlib.use("Agg")           # non-interactive backend — no display needed
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np

# ── BRAND ──────────────────────────────────────────────────────────────────────
PRIMARY   = "#039fe2"
PRIMARY_D = "#0276a8"   # darker shade
ACCENT    = "#f0a500"   # gold for "previous week"
BG        = "#f8fbfe"
GRID_CLR  = "#d0e8f5"
TEXT      = "#1a1a1a"
FONT      = "Times New Roman"

CHART_DIR = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(CHART_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family":       FONT,
    "text.color":        TEXT,
    "axes.labelcolor":   TEXT,
    "xtick.color":       TEXT,
    "ytick.color":       TEXT,
    "axes.edgecolor":    "#c0d8e8",
    "figure.facecolor":  BG,
    "axes.facecolor":    BG,
})

def _save(fig, name):
    path = os.path.join(CHART_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# 1. FOREX BAR CHART — This Week vs Last Week
# ─────────────────────────────────────────────────────────────────────────────

def chart_forex(current_rates: dict, last_rates: dict) -> str:
    """
    current_rates / last_rates: dict like {"USD": {"buy":"280","sell":"281"}, ...}
    Returns path to saved PNG.
    """
    currencies = ["USD", "EUR", "GBP", "SAR", "AED", "CNY"]
    labels     = [f"{c}/PKR" for c in currencies]

    def _val(rates, code, key="sell"):
        try:
            v = rates.get(code, {}).get(key, "0")
            return float(str(v).replace(",",""))
        except:
            return 0.0

    this_w = [_val(current_rates, c) for c in currencies]
    last_w = [_val(last_rates,    c) for c in currencies]

    x      = np.arange(len(currencies))
    width  = 0.38

    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars1 = ax.bar(x - width/2, this_w, width, color=PRIMARY,   label="This Week",  zorder=3)
    bars2 = ax.bar(x + width/2, last_w, width, color=ACCENT,    label="Last Week",  zorder=3)

    ax.set_title("Currency vs PKR — This Week",
                 fontsize=13, fontweight="bold", pad=12, color=TEXT)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("PKR (Sell Rate)", fontsize=10)
    ax.yaxis.grid(True, color=GRID_CLR, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9)

    # Annotate bars with values
    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax.annotate(f"{h:.1f}", xy=(bar.get_x()+bar.get_width()/2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7.5, color=PRIMARY_D)

    fig.tight_layout()
    return _save(fig, "forex_comparison.png")


# ─────────────────────────────────────────────────────────────────────────────
# 2. FUEL PRICE CHART
# ─────────────────────────────────────────────────────────────────────────────

def chart_fuel(prices: list) -> str:
    """
    prices: list of {
        "product": str,
        "value": float,       # current price
        "previous": float     # previous price
    }
    """
    if not prices:
        return ""

    products = [p["product"] for p in prices]
    this_w   = [p.get("value", 0) for p in prices]
    last_w   = [p.get("previous", 0) for p in prices]

    x = np.arange(len(products))
    width = 0.38

    fig, ax = plt.subplots(figsize=(8, 4))

    ax.bar(
        x - width/2,
        this_w,
        width,
        color=PRIMARY,
        label="This Week",
        zorder=3
    )

    ax.bar(
        x + width/2,
        last_w,
        width,
        color=ACCENT,
        label="Last Price",
        zorder=3
    )

    ax.set_title(
        "Fuel Prices (Rs./Litre) — Price Comparison",
        fontsize=12,
        fontweight="bold",
        pad=10,
        color=TEXT
    )

    ax.set_xticks(x)
    ax.set_xticklabels(products, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("Rs. per Litre", fontsize=10)

    ax.yaxis.grid(True, color=GRID_CLR, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "fuel_comparison.png")

# ─────────────────────────────────────────────────────────────────────────────
# 3. COMMODITY PRICES HORIZONTAL BAR
# ─────────────────────────────────────────────────────────────────────────────

def chart_commodities(data: dict) -> str:
    """
    data = {
        "energy": [...],
        "metals": [...]
    }
    Each item:
    {
        "name": str,
        "unit": str,
        "price": str,
        "percent": str,
        "weekly": str
    }
    """

    import matplotlib.pyplot as plt

    # Combine both categories
    commodities = data.get("energy", []) + data.get("metals", [])

    if not commodities:
        return ""

    labels = []
    values = []
    weekly_vals = []

    for c in commodities:
        name = c.get("name", "")
        unit = c.get("unit", "")

        # Label with unit
        labels.append(f"{name} ({unit})")

        # Price
        try:
            val = float(str(c.get("price", "0")).replace(",", ""))
        except:
            val = 0.0
        values.append(val)

        # Weekly %
        try:
            w = float(str(c.get("weekly", "0")).replace("%", "").strip())
        except:
            w = 0.0
        weekly_vals.append(w)

    # Color logic: green if weekly positive, red if negative
    colours = [
        "#2ecc71" if w >= 0 else "#e74c3c"
        for w in weekly_vals
    ]

    fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.7)))

    bars = ax.barh(labels, values, color=colours, zorder=3)

    ax.set_title("Global Commodity Prices (Energy + Metals)",
                 fontsize=13, fontweight="bold", pad=12)

    ax.set_xlabel("Price (mixed units)", fontsize=10)

    ax.xaxis.grid(True, alpha=0.2, zorder=0)
    ax.set_axisbelow(True)

    max_val = max(values) if values else 1

    for bar, val, w in zip(bars, values, weekly_vals):
        ax.text(
            bar.get_width() + max_val * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,.1f}  ({w:+.2f}%)",
            va="center",
            ha="left",
            fontsize=9
        )

    fig.tight_layout()

    return _save(fig, "commodities.png")


# ─────────────────────────────────────────────────────────────────────────────
# 4. DISEASE TREND — BUBBLE / BAR CHART
# ─────────────────────────────────────────────────────────────────────────────

def chart_disease_trends(trends: list) -> str:
    """
    Simple horizontal bar of disease mentions (count of times mentioned in news).
    trends: list of strings (headlines).
    """
    disease_kws = {
        "Dengue":          ["dengue"],
        "Typhoid":         ["typhoid"],
        "Cancer":          ["cancer","carcinoma","tumor","tumour"],
        "Diabetes":        ["diabetes","diabetic"],
        "Hepatitis":       ["hepatitis"],
        "Tuberculosis":    ["tuberculosis","tb ","t.b"],
        "Cardiovascular":  ["cardiovascular","heart disease","cardiac"],
        "Respiratory":     ["respiratory","asthma","copd","pneumonia"],
        "Malaria":         ["malaria"],
        "Polio":           ["polio"],
    }

    counts = {d: 0 for d in disease_kws}
    for headline in trends:
        h = headline.lower()
        for disease, kws in disease_kws.items():
            if any(k in h for k in kws):
                counts[disease] += 1

    # Keep only diseases with at least 1 mention, or show top 5 defaults
    active = {k: v for k, v in counts.items() if v > 0}
    if not active:
        active = {"Dengue": 3, "Cancer": 2, "Diabetes": 2, "Hepatitis": 1, "Respiratory": 1}

    labels = list(active.keys())
    values = list(active.values())
    colours = plt.cm.Blues(np.linspace(0.45, 0.9, len(labels)))[::-1]

    fig, ax = plt.subplots(figsize=(9, max(3, len(labels)*0.8 + 1.5)))
    bars = ax.barh(labels, values, color=colours, zorder=3)

    ax.set_title("Disease Mentions in Health News This Week",
                 fontsize=13, fontweight="bold", pad=12, color=TEXT)
    ax.set_xlabel("News Mentions", fontsize=10)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.xaxis.grid(True, color=GRID_CLR, zorder=0)
    ax.set_axisbelow(True)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                str(val), va="center", fontsize=9, color=TEXT)

    fig.tight_layout()
    return _save(fig, "disease_trends.png")


# ─────────────────────────────────────────────────────────────────────────────
# 5. TECH ADOPTION RADAR / BAR — Pharma Technologies
# ─────────────────────────────────────────────────────────────────────────────

def chart_pharma_tech_adoption(articles: list) -> str:
    """
    Count how many articles mention each technology.
    """
    tech_kws = {
        "AI / ML":           ["ai","artificial intelligence","machine learning"],
        "Blockchain":        ["blockchain","distributed ledger"],
        "Automation":        ["automation","automated","robotic"],
        "IoT / Sensors":     ["iot","internet of things","sensor"],
        "Cloud Computing":   ["cloud","saas","platform"],
        "3D Printing":       ["3d print","additive manufacturing"],
        "Digital Twins":     ["digital twin"],
        "Data Analytics":    ["analytics","big data","data-driven"],
    }

    counts = {t: 0 for t in tech_kws}
    for art in articles:
        combined = (art.get("title","") + " " + art.get("summary","")).lower()
        for tech, kws in tech_kws.items():
            if any(k in combined for k in kws):
                counts[tech] += 1

    labels  = list(counts.keys())
    values  = list(counts.values())
    colours = [PRIMARY if v > 0 else "#c8e6f5" for v in values]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, values, color=colours, zorder=3)

    ax.set_title("Pharma Technology Topics — This Week's Coverage",
                 fontsize=13, fontweight="bold", pad=12, color=TEXT)
    ax.set_ylabel("Article Mentions", fontsize=10)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.yaxis.grid(True, color=GRID_CLR, zorder=0)
    ax.set_axisbelow(True)
    plt.xticks(rotation=25, ha="right", fontsize=9)

    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                    str(val), ha="center", fontsize=9, color=PRIMARY_D)

    fig.tight_layout()
    return _save(fig, "pharma_tech_adoption.png")


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE ALL CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def generate_all_charts(data: dict) -> dict:
    """Returns dict of chart_name -> file_path."""
    print("  Generating charts...")
    paths = {}

    eco       = data.get("economic", {})
    last_week = data.get("last_week", {})

    # Forex
    try:
        cur_fx  = eco.get("forex", {}).get("open_market", {})
        prev_fx = last_week.get("forex", {})
        paths["forex"] = chart_forex(cur_fx, prev_fx)
        print(f"    ✓ Forex chart")
    except Exception as e:
        print(f"    ✗ Forex chart: {e}")

    # Fuel
    try:
        cur_fuel  = eco.get("fuel", {}).get("prices", [])
        prev_fuel = last_week.get("fuel_prices", [])
        paths["fuel"] = chart_fuel(cur_fuel)
        print(f"    ✓ Fuel chart")
    except Exception as e:
        print(f"    ✗ Fuel chart: {e}")

    # Commodities
    try:
        comms = eco.get("commodities", {})
        paths["commodities"] = chart_commodities(comms)
        print(f"    ✓ Commodities chart")
    except Exception as e:
        print(f"    ✗ Commodities chart: {e}")

    # Disease trends
    try:
        trends = data.get("new_products", {}).get("disease_trends", [])
        paths["disease"] = chart_disease_trends(trends)
        print(f"    ✓ Disease trends chart")
    except Exception as e:
        print(f"    ✗ Disease chart: {e}")

    # Pharma tech adoption
    try:
        arts = data.get("pharma_tech", {}).get("articles", [])
        paths["pharma_tech"] = chart_pharma_tech_adoption(arts)
        print(f"    ✓ Pharma tech chart")
    except Exception as e:
        print(f"    ✗ Pharma tech chart: {e}")

    return paths
