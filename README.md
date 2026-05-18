# Pharma Intelligence & Economic Monitoring Report System

An AI-powered web scraping and reporting pipeline that collects economic, pharmaceutical, and technology-related data from multiple public sources and generates automated analytical summaries using Ollama-powered local LLMs.

---

## Overview

This project is designed to automate the collection, analysis, and summarization of key indicators affecting the pharmaceutical industry in Pakistan and globally.

The system scrapes structured and unstructured data from relevant websites, processes the information, and generates AI-assisted reports for market intelligence, economic monitoring, and pharma trend analysis.

The reports help monitor:
- Economic conditions
- Pharmaceutical regulations
- Market movements
- Commodity fluctuations
- Technology trends
- Pharma industry research developments

---

## Core Features

### Web Scraping Engine
- Scrapes data from multiple public sources
- Supports scheduled or manual execution
- Handles structured and semi-structured content

### AI-Powered Summarization
- Uses Ollama local LLMs for:
  - report generation
  - executive summaries
  - trend analysis
  - market insights
  - news condensation

### Automated Report Generation
- Generates daily/weekly intelligence reports
- Produces categorized summaries
- Converts raw data into readable insights

### Modular Pipeline
- Independent scrapers for each data source
- Easy to expand with additional modules

---

# Data Sources & Categories

## Pakistan Economic Indicators

### Fuel Prices in Pakistan
Tracks:
- petrol prices
- diesel prices
- OGRA announcements
- fuel market fluctuations

### Forex Rates in Pakistan
Monitors:
- USD/PKR
- EUR/PKR
- GBP/PKR
- SAR/PKR
- foreign exchange movements

### Commodity Prices
Tracks commodity trends including:
- crude oil
- wheat
- rice
- sugar
- gold
- fertilizer-related commodities

---

## Pharmaceutical Intelligence

### DRAP Updates
Collects:
- regulatory announcements
- pricing notifications
- medicine approvals
- policy updates
- recalls and compliance notices

### Pharma Industry Trends
Tracks:
- pharma technology adoption
- AI in healthcare
- biotech developments
- digital health trends
- manufacturing innovations

### Pharma Research Monitoring
Collects:
- recent pharmaceutical research
- drug development news
- clinical advancements
- scientific publications

### Top Selling Medicines (2025)
Analyzes:
- most sold medicines
- therapeutic categories
- pharmaceutical demand patterns
- market trends

---

## News Monitoring

### Economic News
Scrapes:
- local economic developments
- inflation updates
- trade and finance news
- global economic events affecting Pakistan

### Technology Trends
Tracks:
- emerging technologies
- AI developments
- automation trends
- healthcare technology innovations

---

# Tech Stack

## Backend
- Python

## Libraries
- BeautifulSoup
- Selenium
- Requests
- Pandas
- Newspaper3k

## AI Layer
- Ollama
- Local LLM models

## Data Processing
- JSON
- CSV
- Pandas DataFrames

---

# Project Structure

```bash
# Project Structure

```bash
project/
│
├── charts/
│
├── data/
│   └── last_week.json
│
├── newsletters/
│
├── output/
│   └── _render.html
│
├── styles/
│   └── theme.css
│
├── templates/
│   └── economic.html
│
├── ai.py
├── charts.py
├── main.py
├── main_render.py
├── pdf_generator.py
├── scraper.py
├── weather.py
│
├── .cache.sqlite
├── .weather_cache.sqlite
│
└── README.md
