SELECT c.channel, SUM(s.impressions) impressions, SUM(s.clicks) clicks, ROUND(SUM(s.spend),0) spend,
 ROUND(100.0*SUM(s.clicks)/SUM(s.impressions),2) ctr_pct, ROUND(SUM(s.spend)/SUM(s.clicks),2) cpc
 FROM fact_ad_spend s JOIN dim_campaign c USING(campaign_id) GROUP BY c.channel;
