"""
main.py — Weekly Pharma Intelligence Report — Entry Point

Usage:
    python main.py

Output:
    newsletters/pharma_weekly_YYYY-MM-DD.pdf

Scheduling (Windows Task Scheduler — every Monday 7 AM):
    Program:  python.exe
    Args:     main.py
    Start in: C:\\path\\to\\weekly_report\\

Scheduling (Linux cron — every Monday 7 AM):
    0 7 * * 1 /usr/bin/python3 /path/to/weekly_report/main.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from scraper       import collect_all
from charts        import generate_all_charts
from pdf_generator import generate_pdf

from main_render import render_pdf
from ai import generate_ai_insights


def main():
    print("\n" + "="*60)
    print("  PHARMA INTELLIGENCE WEEKLY REPORT GENERATOR")
    print(f"  {datetime.now().strftime('%A, %d %B %Y  %I:%M %p')}")
    print("="*60 + "\n")

    # 1. Collect all live data
    data = collect_all()
    # ✅ 2. GENERATE AI INSIGHTS (ADD THIS HERE)
    print("Generating AI insights...")
    ai_data = generate_ai_insights(data)
    # merge into main dataset
    data.update(ai_data)

    # 2. Generate comparison charts
    print("Generating charts...")
    chart_paths = generate_all_charts(data)
    print(f"  {len(chart_paths)} charts generated.\n")  

    # 3. Build PDF
    out_dir = os.path.join(os.path.dirname(__file__), "newsletters")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"pharma_weekly_{data['date_short']}.pdf"
    out_path = os.path.join(out_dir, filename)

    # print("Building PDF...")
    # generate_pdf(data, chart_paths, out_path)
    # print("Building PDF...")

    render_pdf(data, chart_paths, out_path)

    print(f"\n{'='*60}")
    print(f"  DONE:  {out_path}")
    print(f"{'='*60}\n")
    return out_path


if __name__ == "__main__":
    main()
