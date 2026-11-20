# MarketLens - Campaign Optimization Recommendation Report

## 1. Objective and data
Unify ad spend, web touchpoints and CRM outcomes to compare channels and attribution models. Data is **synthetic** (90 days, 10 campaigns, 4 channels): 13,202 leads, 1,474 wins, $1,102,021 revenue on $297,413 spend.

## 2. Key findings
- Trend insight: weekly ROAS moved from 3.64x (early weeks) to 3.50x (recent weeks), stable. Best week starts 2026-03-30.
- Overall ROAS **3.71x**, blended CAC **$202**.
- Best campaigns (linear ROAS): Webinar Invite (19.51x), Newsletter Promo (19.15x), YouTube Display (16.25x).
- Weakest campaigns: LinkedIn Leadgen (1.59x), Generic Search (1.13x), Competitor Search (0.84x).
- Channel efficiency:

| channel     |   impressions |   clicks |   spend |   ctr_pct |   cpc |
|:------------|--------------:|---------:|--------:|----------:|------:|
| Display     |       1443379 |     7825 |    5821 |      0.54 |  0.74 |
| Email       |       1457451 |    65723 |   21576 |      4.51 |  0.33 |
| Paid Search |       2127141 |    80872 |  204488 |      3.8  |  2.53 |
| Social      |       2146800 |    28717 |   65527 |      1.34 |  2.28 |

## 3. Attribution comparison
| Campaign | Channel | Spend | ROAS first | ROAS last | ROAS linear | CAC (linear) | Payback (months) |
|---|---|---|---|---|---|---|---|
| Webinar Invite | Email | $12,790 | 15.4 | 25.89 | 19.51 | $38 | 0.6 |
| Newsletter Promo | Email | $8,786 | 17.45 | 21.97 | 19.15 | $38 | 0.6 |
| YouTube Display | Display | $3,014 | 27.18 | 0.88 | 16.25 | $50 | 0.7 |
| Partner Banners | Display | $2,807 | 22.01 | 0.51 | 14.41 | $50 | 0.8 |
| Instagram Awareness | Social | $7,766 | 9.02 | 0.57 | 5.6 | $124 | 2.1 |
| Brand Search | Paid Search | $49,970 | 3.72 | 7.02 | 4.99 | $150 | 2.4 |
| Facebook Retargeting | Social | $21,264 | 5.14 | 3.34 | 4.35 | $179 | 2.8 |
| LinkedIn Leadgen | Social | $36,497 | 1.81 | 1.0 | 1.59 | $434 | 7.6 |
| Generic Search | Paid Search | $75,141 | 1.25 | 0.92 | 1.13 | $700 | 10.6 |
| Competitor Search | Paid Search | $79,377 | 1.05 | 0.52 | 0.84 | $914 | 14.3 |

Conclusions change by model. The biggest gap between first-touch and last-touch is **YouTube Display** (27.18x first vs 0.88x last): it introduces customers but rarely closes them, so judging it only on last-touch would undervalue it.

## 4. Underperforming campaigns (linear ROAS < 1.5)
- Generic Search: spend $75,141, ROAS 1.13x, CAC $700
- Competitor Search: spend $79,377, ROAS 0.84x, CAC $914

## 5. Budget reallocation recommendation
Weekly plan (moves 15% of the two weakest campaigns' weekly budget to the two strongest):

| campaign          | action       |   weekly_budget_change_usd |   roas_linear |
|:------------------|:-------------|---------------------------:|--------------:|
| Competitor Search | Decrease 15% |                       -926 |          0.84 |
| Generic Search    | Decrease 15% |                       -877 |          1.13 |
| Newsletter Promo  | Increase     |                        893 |         19.15 |
| Webinar Invite    | Increase     |                        910 |         19.51 |

Channel benchmark (linear attribution):

| channel     |   spend |   revenue |   customers |   roas |   cac |
|:------------|--------:|----------:|------------:|-------:|------:|
| Display     |    5821 |     89431 |         116 |  15.36 |    50 |
| Email       |   21576 |    417771 |         566 |  19.36 |    38 |
| Paid Search |  204488 |    400983 |         527 |   1.96 |   388 |
| Social      |   65527 |    193836 |         266 |   2.96 |   247 |

- Cut 15-20% of spend from Competitor Search and Generic Search.
- Move it to Webinar Invite and Newsletter Promo, then monitor CAC weekly for diminishing returns.
- Do not cut upper-funnel campaigns (see section 3) without testing the effect on downstream conversions.

## 6. Limitations and next steps
Synthetic data; only 3 simple attribution rules (no time-decay or Markov); revenue is one-time so payback is approximate; no real-time feed (alerts are a weekly table). Next: time-decay attribution, incrementality tests, live data connection.
