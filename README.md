# SANIYA SHAHEEN KHAN

# MarketLens - Campaign Performance \& Attribution Analytics

Marketing analytics pipeline: unify ad spend, web touchpoints and CRM data; analyse funnel, CAC, ROAS; compare first-touch, last-touch and linear attribution; recommend budget moves.

## Tools

Python (pandas, numpy), SQLite, HTML/Chart.js dashboard (CSVs in data/clean can also be loaded into Power BI).

## How to run

&#x20;   pip install pandas numpy tabulate
    python pipeline.py

Open `dashboard/dashboard.html` in a browser (needs internet for Chart.js).

## Structure

* data/raw: synthetic ad\_spend, crm\_leads, web\_touchpoints (messy UTMs), campaign\_master
* data/clean: cleaned tables, UTM mapping, query results, attribution results, weekly alerts
* marketlens.db: SQLite data mart (dim\_campaign, fact\_ad\_spend, fact\_leads, fact\_touchpoints)
* sql/: funnel, CAC and drop-off queries
* dashboard/dashboard.html: executive KPIs, funnel, attribution comparison, campaign table with flags
* reports/recommendation\_report.md: findings and budget recommendations

## Funnel

Impression -> Click -> Lead -> SQL -> Win

## Key insight

Instagram Awareness, YouTube Display and Partner Banners look poor under last-touch (ROAS \~0.5-0.9) but strong under first-touch. Generic and Competitor Search are the weakest under every model.

## Limitations

Synthetic data; simple attribution rules; alerts are a weekly table (no real-time feed).

