SELECT strftime('%Y-%W', date) week, MIN(date(date)) week_start, ROUND(SUM(spend),0) spend FROM fact_ad_spend GROUP BY 1;
