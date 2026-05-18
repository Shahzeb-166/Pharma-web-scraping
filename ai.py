import requests
import json

OLLAMA_URL = ""
MODEL = "llama3.1:8b"


# --------------------------------------------------
# CORE CALL (IMPROVED)
# --------------------------------------------------
def ask_ollama(prompt: str) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,
                    "top_p": 0.9
                }
            },
            timeout=60
        )

        data = response.json()
        return clean_output(data.get("response", ""))

    except Exception as e:
        print(f"[AI ERROR] {e}")
        return "AI analysis unavailable."


# --------------------------------------------------
# OUTPUT CLEANER
# --------------------------------------------------
def clean_output(text: str) -> str:
    text = text.replace("\n", " ").strip()
    return " ".join(text.split())


# --------------------------------------------------
# INPUT COMPRESSOR (LESS NOISE)
# --------------------------------------------------
def compress_articles(articles, limit=12):
    cleaned = []
    for a in articles[:limit]:
        title = a.get("title", "")
        summary = a.get("summary", "")
        cleaned.append(f"{title}. {summary[:100]}")
    return cleaned


# --------------------------------------------------
# 1. ECONOMIC SUMMARY (PROFESSIONAL)
# --------------------------------------------------
def economic_summary(data):
    eco = data.get("economic", {})

    prompt = f"""
Role: Senior Macroeconomic Analyst (IMF-style)

Task: Produce a tightly written, high-signal economic assessment.

Constraints:
- Single paragraph only
- 140–160 words
- No bullets, no headings
- No repetition or filler
- Each sentence must add new information

Avoid:
- "overall", "in conclusion", "this highlights"

Focus:
- Pakistan inflation, currency pressure, energy prices
- Global macro conditions (rates, trade, commodities)
- Transmission into Pakistan
- Clear cause-effect relationships

Tone:
- Analytical, concise, institutional

Data:
{json.dumps(eco)[:2500]}
"""
    return ask_ollama(prompt)


# --------------------------------------------------
# 2. GLOBAL ECONOMIC SUMMARY
# --------------------------------------------------
def global_economic_summary(data):
    articles = data.get("economic", {}).get("global", {}).get("articles", [])
    combined = compress_articles(articles)

    prompt = f"""
Role: Global Macroeconomic Strategist

Task: Deliver a concise global macro intelligence brief.

Constraints:
- Single paragraph
- 90–110 words
- No repetition, no filler

Focus:
- Global growth trajectory
- US, China, EU, India dynamics
- Interest rates, inflation, energy markets
- Trade/geopolitics
- Impact on emerging markets (esp. South Asia)

Style:
- Bloomberg / IMF tone
- Insight-driven, not descriptive

Data:
{combined}
"""
    return ask_ollama(prompt)


# --------------------------------------------------
# 3. PHARMA TECH TRENDS (SHARP)
# --------------------------------------------------
def pharma_tech_summary(data):
    tech = data.get("pharma_tech", {}).get("articles", [])
    tech = compress_articles(tech)

    prompt = f"""
Role: Pharmaceutical Strategy Analyst

Task: Extract high-value innovation themes.

Constraints:
- Max 6 bullets
- Each bullet ≤ 6 words
- No explanation
- Avoid generic words like "AI", "digital"

Focus:
- Specific technologies or modalities
- Forward-looking innovation only

Style:
- Executive-ready, sharp

Data:
{tech}
"""
    return ask_ollama(prompt)


# --------------------------------------------------
# 4. DISEASE SUMMARY (STRUCTURED)
# --------------------------------------------------
def disease_summary(data):
    diseases = data.get("new_products", {}).get("pharma_tech", [])

    prompt = f"""
Role: Global Epidemiology Analyst

Task:
1) List top 8 diseases
2) Provide a concise intelligence summary

Constraints:
- Disease list as bullets only
- Summary max 130 words
- No repetition
- No per-disease explanation

Focus:
- Outbreak trends
- Resurgence patterns
- Regional clustering
- Research intensity

Style:
- WHO / CDC tone

Data:
{diseases[:30]}
"""
    return ask_ollama(prompt)


# --------------------------------------------------
# 5. RESEARCH / PIPELINE SUMMARY
# --------------------------------------------------
def research_summary(data):
    pipeline = data.get("new_products", {}).get("pipeline", [])
    launches = data.get("new_products", {}).get("launches", [])

    combined = compress_articles(pipeline + launches)

    prompt = f"""
Role: Pharmaceutical R&D Strategist

Task: Extract core innovation directions.

Constraints:
- Bullet list only
- Max 8 bullets
- Each bullet ≤ 8 words
- No explanation

Focus:
- Drug modalities
- Platform technologies
- Clinical strategy shifts
- Manufacturing innovation

Style:
- McKinsey / IQVIA level precision

Data:
{combined}
"""
    return ask_ollama(prompt)


# --------------------------------------------------
# MASTER FUNCTION
# --------------------------------------------------
def generate_ai_insights(data: dict) -> dict:
    print("Generating AI Insights...")

    return {
        "economic_ai_summary": economic_summary(data),
        "global_ai_summary": global_economic_summary(data),
        "tech_ai_summary": pharma_tech_summary(data),
        "disease_ai_summary": disease_summary(data),
        "research_ai_summary": research_summary(data),
    }
