WITH lt AS (SELECT lead_id, campaign_id FROM (SELECT lead_id, campaign_id,
 ROW_NUMBER() OVER (PARTITION BY lead_id ORDER BY touch_date DESC) rn FROM fact_touchpoints) WHERE rn=1),
 sp AS (SELECT campaign_id, SUM(impressions) impressions, SUM(clicks) clicks, SUM(spend) spend FROM fact_ad_spend GROUP BY 1)
 SELECT c.campaign_name, c.channel, sp.impressions, sp.clicks, COUNT(l.lead_id) leads, SUM(l.is_sql) sqls, SUM(l.is_won) wins,
 ROUND(sp.spend,0) spend, ROUND(1.0*sp.spend/NULLIF(SUM(l.is_won),0),0) cac,
 ROUND(100.0*COUNT(l.lead_id)/sp.clicks,2) click_to_lead_pct, ROUND(100.0*SUM(l.is_sql)/COUNT(l.lead_id),1) lead_to_sql_pct,
 ROUND(100.0*SUM(l.is_won)/NULLIF(SUM(l.is_sql),0),1) sql_to_win_pct
 FROM lt JOIN fact_leads l USING(lead_id) JOIN dim_campaign c ON c.campaign_id=lt.campaign_id JOIN sp ON sp.campaign_id=c.campaign_id
 GROUP BY c.campaign_id ORDER BY wins DESC;
