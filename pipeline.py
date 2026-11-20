"""MarketLens: end-to-end pipeline. Run:  python pipeline.py
Steps: generate raw data -> clean/normalize UTM -> SQLite data mart -> funnel/CAC SQL
       -> attribution (first/last/linear) -> ROAS/CAC/payback -> dashboard + report"""
import os, json, sqlite3
import numpy as np, pandas as pd
from datetime import timedelta

B = os.path.dirname(os.path.abspath(__file__))
for p in ["data/raw", "data/clean", "sql", "dashboard", "reports"]:
    os.makedirs(f"{B}/{p}", exist_ok=True)

# ---------------- 1. GENERATE RAW DATA (synthetic) ----------------
rng = np.random.default_rng(42)
dates = pd.date_range("2026-04-01", periods=90)
camp = [(1,"Brand Search","Paid Search",.06,1.2,.10),(2,"Generic Search","Paid Search",.03,3.5,.04),
        (3,"Competitor Search","Paid Search",.025,4.5,.03),(4,"Instagram Awareness","Social",.012,.9,.015),
        (5,"Facebook Retargeting","Social",.02,1.5,.06),(6,"LinkedIn Leadgen","Social",.008,6.0,.07),
        (7,"Newsletter Promo","Email",.04,.3,.08),(8,"Webinar Invite","Email",.05,.35,.10),
        (9,"YouTube Display","Display",.006,.7,.01),(10,"Partner Banners","Display",.005,.8,.012)]
C = pd.DataFrame(camp, columns=["campaign_id","campaign_name","channel","ctr","cpc","lead_rate"])
messy = {"Paid Search":["google","Google","GOOGLE_ads","google "],"Social":["fb","Facebook","facebook","LinkedIn","linkedin"],
         "Email":["email","Email","newsletter"],"Display":["youtube","YouTube","partner","Partner "]}
sp, ld, tc = [], [], []
lid = 1
for d in dates:
    for c in C.itertuples():
        imp = max(int(rng.normal(8000, 1500)), 1000)
        clk = int(rng.binomial(imp, c.ctr))
        sp.append((d, c.campaign_id, imp, clk, round(clk*c.cpc*rng.uniform(.9,1.1), 2)))
        for _ in range(rng.binomial(clk, c.lead_rate)):
            sql_ = rng.random() < .45
            won = sql_ and rng.random() < .25
            rev = round(rng.lognormal(6.5, .5)) if won else 0
            ld.append((lid, d, rng.choice(["Mobile","Desktop","Tablet"],p=[.55,.35,.10]),
                       rng.choice(["India","USA","UK","Germany"],p=[.4,.3,.2,.1]),
                       rng.choice(["SMB","Mid-Market","Enterprise"],p=[.5,.3,.2]), int(sql_), int(won), rev,
                       d+timedelta(days=int(rng.integers(5,45))) if won else None))
            for _ in range(rng.integers(0,3)):
                tc.append((lid, d-timedelta(days=int(rng.integers(1,15))), int(rng.choice(C.campaign_id))))
            tc.append((lid, d, c.campaign_id)); lid += 1
spend = pd.DataFrame(sp, columns=["date","campaign_id","impressions","clicks","spend"])
leads = pd.DataFrame(ld, columns=["lead_id","created_date","device","country","audience","is_sql","is_won","revenue","won_date"])
touch = pd.DataFrame(tc, columns=["lead_id","touch_date","campaign_id"])
ch, nm = C.set_index("campaign_id").channel, C.set_index("campaign_id").campaign_name
touch["utm_source"] = touch.campaign_id.map(lambda i: rng.choice(messy[ch[i]]))
touch["utm_campaign"] = touch.campaign_id.map(lambda i: rng.choice([nm[i].lower().replace(" ","_"), nm[i].replace(" ","-"), nm[i].upper()]))
master = C[["campaign_id","campaign_name","channel"]]
spend.to_csv(f"{B}/data/raw/ad_spend.csv", index=False); leads.to_csv(f"{B}/data/raw/crm_leads.csv", index=False)
touch.drop(columns="campaign_id").to_csv(f"{B}/data/raw/web_touchpoints.csv", index=False)
master.to_csv(f"{B}/data/raw/campaign_master.csv", index=False)

# ---------------- 2. CLEAN & NORMALIZE ----------------
raw = pd.read_csv(f"{B}/data/raw/web_touchpoints.csv", parse_dates=["touch_date"])
raw["utm_source"] = raw.utm_source.str.strip().str.lower()
raw["utm_campaign"] = raw.utm_campaign.str.strip().str.lower().str.replace(r"[-\s]+", "_", regex=True)
key = master.assign(k=master.campaign_name.str.lower().str.replace(" ", "_")).set_index("k").campaign_id
raw["campaign_id"] = raw.utm_campaign.map(key)
utm_map = {"google":"Paid Search","google_ads":"Paid Search","fb":"Social","facebook":"Social","linkedin":"Social",
           "email":"Email","newsletter":"Email","youtube":"Display","partner":"Display"}
raw["channel"] = raw.utm_source.map(utm_map)
assert raw.campaign_id.notna().all() and raw.channel.notna().all(), "unmapped UTM values"
raw = raw.drop_duplicates()
pd.DataFrame(list(utm_map.items()), columns=["utm_source","channel"]).to_csv(f"{B}/data/clean/utm_mapping.csv", index=False)
clean_touch = raw[["lead_id","touch_date","campaign_id","channel"]]

# ---------------- 3. DATA MART (SQLite) ----------------
db = f"{B}/marketlens.db"
if os.path.exists(db): os.remove(db)
con = sqlite3.connect(db)
tables = {"dim_campaign": master, "fact_ad_spend": spend, "fact_leads": leads, "fact_touchpoints": clean_touch}
for n, df in tables.items():
    df.to_csv(f"{B}/data/clean/{n}.csv", index=False)
    df.to_sql(n, con, index=False)

# ---------------- 4. FUNNEL / CAC SQL ----------------
Q = {}
Q["01_spend_by_channel"] = """SELECT c.channel, SUM(s.impressions) impressions, SUM(s.clicks) clicks, ROUND(SUM(s.spend),0) spend,
 ROUND(100.0*SUM(s.clicks)/SUM(s.impressions),2) ctr_pct, ROUND(SUM(s.spend)/SUM(s.clicks),2) cpc
 FROM fact_ad_spend s JOIN dim_campaign c USING(campaign_id) GROUP BY c.channel;"""
Q["02_funnel_by_campaign_lasttouch"] = """WITH lt AS (SELECT lead_id, campaign_id FROM (SELECT lead_id, campaign_id,
 ROW_NUMBER() OVER (PARTITION BY lead_id ORDER BY touch_date DESC) rn FROM fact_touchpoints) WHERE rn=1),
 sp AS (SELECT campaign_id, SUM(impressions) impressions, SUM(clicks) clicks, SUM(spend) spend FROM fact_ad_spend GROUP BY 1)
 SELECT c.campaign_name, c.channel, sp.impressions, sp.clicks, COUNT(l.lead_id) leads, SUM(l.is_sql) sqls, SUM(l.is_won) wins,
 ROUND(sp.spend,0) spend, ROUND(1.0*sp.spend/NULLIF(SUM(l.is_won),0),0) cac,
 ROUND(100.0*COUNT(l.lead_id)/sp.clicks,2) click_to_lead_pct, ROUND(100.0*SUM(l.is_sql)/COUNT(l.lead_id),1) lead_to_sql_pct,
 ROUND(100.0*SUM(l.is_won)/NULLIF(SUM(l.is_sql),0),1) sql_to_win_pct
 FROM lt JOIN fact_leads l USING(lead_id) JOIN dim_campaign c ON c.campaign_id=lt.campaign_id JOIN sp ON sp.campaign_id=c.campaign_id
 GROUP BY c.campaign_id ORDER BY wins DESC;"""
for dim in ["device", "country", "audience"]:
    Q[f"03_dropoff_by_{dim}"] = f"""SELECT {dim}, COUNT(*) leads, SUM(is_sql) sqls, SUM(is_won) wins,
 ROUND(100.0*SUM(is_sql)/COUNT(*),1) lead_to_sql_pct, ROUND(100.0*SUM(is_won)/NULLIF(SUM(is_sql),0),1) sql_to_win_pct
 FROM fact_leads GROUP BY {dim};"""
Q["04_weekly_spend"] = """SELECT strftime('%Y-%W', date) week, MIN(date(date)) week_start, ROUND(SUM(spend),0) spend FROM fact_ad_spend GROUP BY 1;"""
R = {}
for k, q in Q.items():
    open(f"{B}/sql/{k}.sql", "w").write(q + "\n")
    R[k] = pd.read_sql(q, con)
funnel = R["02_funnel_by_campaign_lasttouch"]

# ---------------- 5. ATTRIBUTION ----------------
t = pd.read_sql("SELECT lead_id, touch_date, campaign_id FROM fact_touchpoints", con).sort_values(["lead_id","touch_date"])
t["n"] = t.groupby("lead_id").campaign_id.transform("count"); t["pos"] = t.groupby("lead_id").cumcount()
t = t.merge(pd.read_sql("SELECT lead_id, revenue FROM fact_leads WHERE is_won=1", con), on="lead_id")
t["w_first"] = (t.pos == 0)*1.0; t["w_last"] = (t.pos == t.n-1)*1.0; t["w_linear"] = 1.0/t.n
for m in ["first","last","linear"]:
    t[f"rev_{m}"] = t[f"w_{m}"]*t.revenue
A = t.groupby("campaign_id")[[c for c in t.columns if c.startswith(("w_","rev_"))]].sum()
A = A.join(master.set_index("campaign_id")).join(spend.groupby("campaign_id").spend.sum()).reset_index()
for m in ["first","last","linear"]:
    A[f"roas_{m}"] = (A[f"rev_{m}"]/A.spend).round(2)
    A[f"cac_{m}"] = (A.spend/A[f"w_{m}"]).round(0)
A["payback_months_linear"] = (A.cac_linear/((A.rev_linear/A.w_linear)/12)).round(1)
A["spend"] = A.spend.round(0)
A["flag"] = np.where(A.roas_linear < 1.5, "UNDERPERFORMING", "OK")
A.round(2).to_csv(f"{B}/data/clean/attribution_results.csv", index=False)
A[A.flag != "OK"][["campaign_name","spend","roas_last","roas_linear","cac_linear"]].to_csv(f"{B}/data/clean/weekly_alerts.csv", index=False)
for k, df in R.items(): df.to_csv(f"{B}/data/clean/{k}.csv", index=False)

# ---------------- 6. DASHBOARD ----------------
tot_sp, tot_rev, wins = spend.spend.sum(), leads.revenue.sum(), int(leads.is_won.sum())
wk = leads.assign(w=leads.created_date.dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")).groupby("w").revenue.sum()
wsp = spend.assign(w=spend.date.dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")).groupby("w").spend.sum()

# ---- extras: channel benchmark, weekly reallocation, trend insight, diagram ----
CH = A.groupby("channel").agg(spend=("spend","sum"), revenue=("rev_linear","sum"), customers=("w_linear","sum")).reset_index()
CH["roas"] = (CH.revenue/CH.spend).round(2); CH["cac"] = (CH.spend/CH.customers).round(0)
CH[["spend","revenue","customers"]] = CH[["spend","revenue","customers"]].round(0)
CH.to_csv(f"{B}/data/clean/channel_benchmark.csv", index=False)
nweeks = len(dates)/7
s2 = A.sort_values("roas_linear"); losers, winners = s2.head(2), s2.tail(2)
plan, cut_total = [], 0
for r in losers.itertuples():
    cut = round(r.spend/nweeks*.15); cut_total += cut
    plan.append((r.campaign_name, "Decrease 15%", -cut, r.roas_linear))
for r in winners.itertuples():
    plan.append((r.campaign_name, "Increase", round(cut_total*r.roas_linear/winners.roas_linear.sum()), r.roas_linear))
PLAN = pd.DataFrame(plan, columns=["campaign","action","weekly_budget_change_usd","roas_linear"])
PLAN.to_csv(f"{B}/data/clean/weekly_reallocation_plan.csv", index=False)
rr = [wk.get(w,0)/wsp[w] for w in wsp.index]
f4, l4 = np.mean(rr[1:5]), np.mean(rr[-5:-1])
trend = (f"Trend insight: weekly ROAS moved from {f4:.2f}x (early weeks) to {l4:.2f}x (recent weeks), "
         + ("improving" if l4>f4*1.05 else "declining" if l4<f4*.95 else "stable") + f". Best week starts {wsp.index[int(np.argmax(rr))]}.")
svg = """<svg xmlns='http://www.w3.org/2000/svg' width='760' height='330' font-family='sans-serif' font-size='13'>
<rect width='760' height='330' fill='white'/>
<rect x='300' y='20' width='160' height='90' fill='#dbe7ff' stroke='#1f3a5f'/><text x='312' y='42' font-weight='bold'>dim_campaign</text><text x='312' y='62'>campaign_id (PK)</text><text x='312' y='80'>campaign_name</text><text x='312' y='98'>channel</text>
<rect x='20' y='200' width='200' height='110' fill='#e3f6e8' stroke='#2e7d32'/><text x='32' y='222' font-weight='bold'>fact_ad_spend</text><text x='32' y='242'>date, campaign_id (FK)</text><text x='32' y='260'>impressions, clicks</text><text x='32' y='278'>spend</text>
<rect x='280' y='200' width='200' height='110' fill='#e3f6e8' stroke='#2e7d32'/><text x='292' y='222' font-weight='bold'>fact_touchpoints</text><text x='292' y='242'>lead_id (FK)</text><text x='292' y='260'>campaign_id (FK)</text><text x='292' y='278'>touch_date, channel</text>
<rect x='540' y='200' width='200' height='110' fill='#e3f6e8' stroke='#2e7d32'/><text x='552' y='222' font-weight='bold'>fact_leads</text><text x='552' y='242'>lead_id (PK), created_date</text><text x='552' y='260'>device, country, audience</text><text x='552' y='278'>is_sql, is_won, revenue</text>
<g stroke='#555' stroke-width='2'><line x1='340' y1='110' x2='120' y2='200'/><line x1='380' y1='110' x2='380' y2='200'/><line x1='480' y1='255' x2='540' y2='255'/></g>
<text x='190' y='150'>campaign_id</text><text x='386' y='160'>campaign_id</text><text x='490' y='248'>lead_id</text></svg>"""
open(f"{B}/reports/data_mart_diagram.svg","w").write(svg)
D = dict(trend=trend, channel=CH.to_dict('records'), plan=PLAN.to_dict('records'), kpi=dict(spend=round(tot_sp), revenue=int(tot_rev), roas=round(tot_rev/tot_sp,2), cac=round(tot_sp/wins), wins=wins, leads=len(leads)),
         weeks=list(wsp.index), wspend=[round(x) for x in wsp], wrev=[int(wk.get(w,0)) for w in wsp.index],
         funnel=dict(Clicks=int(spend.clicks.sum()), Leads=len(leads), SQLs=int(leads.is_sql.sum()), Wins=wins),
         attr=A[["campaign_name","channel","spend","rev_first","rev_last","rev_linear","roas_first","roas_last","roas_linear","cac_linear","payback_months_linear","flag"]].round(1).to_dict("records"),
         dims={d: R[f"03_dropoff_by_{d}"].to_dict("records") for d in ["device","country","audience"]})
html = """<!doctype html><html><head><meta charset=utf-8><title>MarketLens Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>body{font-family:system-ui,sans-serif;margin:0;background:#f4f6f9;color:#222}h1{margin:0;padding:16px 24px;background:#1f3a5f;color:#fff;font-size:20px}
.w{padding:16px 24px}.k{display:flex;gap:12px;flex-wrap:wrap}.c{background:#fff;border-radius:8px;padding:14px;box-shadow:0 1px 3px #0002}
.k .c{flex:1;min-width:130px}.k b{font-size:22px;display:block}.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:12px;margin-top:12px}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:6px;border-bottom:1px solid #eee;text-align:right}td:first-child,th:first-child{text-align:left}
.bad{background:#fde2e2;color:#b00020;font-weight:600}.ok{background:#e3f6e8}h3{margin:0 0 8px;font-size:15px}</style></head><body>
<h1>MarketLens - Campaign Performance & Attribution</h1><div class=w><div class=c id=tr style="margin-bottom:12px;font-weight:600"></div><div class=c style="margin-bottom:12px">Filter by channel: <select id=sel></select></div><div class=k id=k></div>
<div class=g><div class=c><h3>Weekly spend vs revenue</h3><canvas id=a></canvas></div><div class=c><h3>Funnel</h3><canvas id=b></canvas></div>
<div class=c style="grid-column:1/-1"><h3>Revenue by campaign: first-touch vs last-touch vs linear</h3><canvas id=d></canvas></div>
<div class=c><h3>Lead to SQL % by device / audience</h3><canvas id=e></canvas></div><div class=c><h3>Lead to SQL % by country</h3><canvas id=f></canvas></div>
<div class=c><h3>Channel benchmark</h3><table id=ct></table></div><div class=c><h3>Weekly budget reallocation plan</h3><table id=pl></table></div><div class=c style="grid-column:1/-1"><h3>Campaign performance (red = linear ROAS &lt; 1.5)</h3><table id=t></table></div></div></div>
<script>const D=__DATA__;const $=i=>document.getElementById(i),f=n=>n.toLocaleString();
$('k').innerHTML=[['Spend','$'+f(D.kpi.spend)],['Revenue','$'+f(D.kpi.revenue)],['ROAS',D.kpi.roas+'x'],['CAC','$'+f(D.kpi.cac)],['Leads',f(D.kpi.leads)],['Wins',f(D.kpi.wins)]].map(x=>`<div class=c>${x[0]}<b>${x[1]}</b></div>`).join('');
new Chart($('a'),{type:'line',data:{labels:D.weeks,datasets:[{label:'Spend',data:D.wspend,borderColor:'#d9534f'},{label:'Revenue',data:D.wrev,borderColor:'#2e7d32'}]}});
new Chart($('b'),{type:'bar',data:{labels:Object.keys(D.funnel),datasets:[{label:'Count',data:Object.values(D.funnel),backgroundColor:'#1f3a5f'}]},options:{indexAxis:'y'}});
const cols=[['First-touch','rev_first','#5b8def'],['Last-touch','rev_last','#f0a30a'],['Linear','rev_linear','#2e7d32']];let ch;
function draw(){const v=$('sel').value,R=D.attr.filter(r=>v=='All'||r.channel==v);if(ch)ch.destroy();
ch=new Chart($('d'),{type:'bar',data:{labels:R.map(r=>r.campaign_name),datasets:cols.map(x=>({label:x[0],data:R.map(r=>r[x[1]]),backgroundColor:x[2]}))}});
$('t').innerHTML='<tr><th>Campaign<th>Channel<th>Spend<th>ROAS first<th>ROAS last<th>ROAS linear<th>CAC<th>Payback (mo)<th>Status</tr>'+R.map(r=>`<tr><td>${r.campaign_name}<td>${r.channel}<td>$${f(r.spend)}<td>${r.roas_first}<td>${r.roas_last}<td class=${r.flag=='OK'?'ok':'bad'}>${r.roas_linear}<td>$${f(r.cac_linear)}<td>${r.payback_months_linear}<td class=${r.flag=='OK'?'ok':'bad'}>${r.flag}</tr>`).join('');}
$('sel').innerHTML='<option>All</option>'+[...new Set(D.attr.map(r=>r.channel))].map(c=>`<option>${c}</option>`).join('');$('sel').onchange=draw;draw();
$('tr').textContent=D.trend;
$('ct').innerHTML='<tr><th>Channel<th>Spend<th>Revenue<th>Customers<th>ROAS<th>CAC</tr>'+D.channel.map(r=>`<tr><td>${r.channel}<td>$${f(r.spend)}<td>$${f(r.revenue)}<td>${f(r.customers)}<td>${r.roas}<td>$${f(r.cac)}</tr>`).join('');
$('pl').innerHTML='<tr><th>Campaign<th>Action<th>Weekly change<th>ROAS</tr>'+D.plan.map(r=>`<tr><td>${r.campaign}<td>${r.action}<td class=${r.weekly_budget_change_usd<0?'bad':'ok'}>$${f(r.weekly_budget_change_usd)}<td>${r.roas_linear}</tr>`).join('');
const dl=[...D.dims.device.map(r=>['Dev: '+r.device,r.lead_to_sql_pct]),...D.dims.audience.map(r=>['Aud: '+r.audience,r.lead_to_sql_pct])];
new Chart($('e'),{type:'bar',data:{labels:dl.map(x=>x[0]),datasets:[{label:'Lead to SQL %',data:dl.map(x=>x[1]),backgroundColor:'#6a5acd'}]}});
new Chart($('f'),{type:'bar',data:{labels:D.dims.country.map(r=>r.country),datasets:[{label:'Lead to SQL %',data:D.dims.country.map(r=>r.lead_to_sql_pct),backgroundColor:'#00897b'}]}});
</script></body></html>"""
open(f"{B}/dashboard/dashboard.html", "w").write(html.replace("__DATA__", json.dumps(D, default=str)))

# ---------------- 7. REPORT ----------------
s = A.sort_values("roas_linear", ascending=False)
top, bot = s.head(3), s.tail(3)
chg = A.assign(d=A.roas_first-A.roas_last).sort_values("d", ascending=False).iloc[0]
tbl = "\n".join(f"| {r.campaign_name} | {r.channel} | ${r.spend:,.0f} | {r.roas_first} | {r.roas_last} | {r.roas_linear} | ${r.cac_linear:,.0f} | {r.payback_months_linear} |" for r in s.itertuples())
ch_t = R["01_spend_by_channel"].to_markdown(index=False) if hasattr(pd.DataFrame, "to_markdown") else R["01_spend_by_channel"].to_string(index=False)
rep = f"""# MarketLens - Campaign Optimization Recommendation Report

## 1. Objective and data
Unify ad spend, web touchpoints and CRM outcomes to compare channels and attribution models. Data is **synthetic** (90 days, 10 campaigns, 4 channels): {len(leads):,} leads, {wins:,} wins, ${tot_rev:,.0f} revenue on ${tot_sp:,.0f} spend.

## 2. Key findings
- {trend}
- Overall ROAS **{tot_rev/tot_sp:.2f}x**, blended CAC **${tot_sp/wins:,.0f}**.
- Best campaigns (linear ROAS): {', '.join(f'{r.campaign_name} ({r.roas_linear}x)' for r in top.itertuples())}.
- Weakest campaigns: {', '.join(f'{r.campaign_name} ({r.roas_linear}x)' for r in bot.itertuples())}.
- Channel efficiency:

{ch_t}

## 3. Attribution comparison
| Campaign | Channel | Spend | ROAS first | ROAS last | ROAS linear | CAC (linear) | Payback (months) |
|---|---|---|---|---|---|---|---|
{tbl}

Conclusions change by model. The biggest gap between first-touch and last-touch is **{chg.campaign_name}** ({chg.roas_first}x first vs {chg.roas_last}x last): it introduces customers but rarely closes them, so judging it only on last-touch would undervalue it.

## 4. Underperforming campaigns (linear ROAS < 1.5)
{chr(10).join(f'- {r.campaign_name}: spend ${r.spend:,.0f}, ROAS {r.roas_linear}x, CAC ${r.cac_linear:,.0f}' for r in A[A.flag!='OK'].itertuples()) or '- None'}

## 5. Budget reallocation recommendation
Weekly plan (moves 15% of the two weakest campaigns' weekly budget to the two strongest):

{PLAN.to_markdown(index=False)}

Channel benchmark (linear attribution):

{CH.to_markdown(index=False)}

- Cut 15-20% of spend from {bot.iloc[-1].campaign_name} and {bot.iloc[-2].campaign_name}.
- Move it to {top.iloc[0].campaign_name} and {top.iloc[1].campaign_name}, then monitor CAC weekly for diminishing returns.
- Do not cut upper-funnel campaigns (see section 3) without testing the effect on downstream conversions.

## 6. Limitations and next steps
Synthetic data; only 3 simple attribution rules (no time-decay or Markov); revenue is one-time so payback is approximate; no real-time feed (alerts are a weekly table). Next: time-decay attribution, incrementality tests, live data connection.
"""
open(f"{B}/reports/recommendation_report.md", "w").write(rep)
print(A[["campaign_name","spend","roas_first","roas_last","roas_linear","cac_linear","flag"]].to_string(index=False))
print("KPI", D["kpi"])
