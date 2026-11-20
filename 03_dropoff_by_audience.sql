SELECT audience, COUNT(*) leads, SUM(is_sql) sqls, SUM(is_won) wins,
 ROUND(100.0*SUM(is_sql)/COUNT(*),1) lead_to_sql_pct, ROUND(100.0*SUM(is_won)/NULLIF(SUM(is_sql),0),1) sql_to_win_pct
 FROM fact_leads GROUP BY audience;
