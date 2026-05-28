#!/usr/bin/env python3
import anthropic, json, re, time
from datetime import datetime, timezone, timedelta
 
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
DAYS_KO = ['월','화','수','목','금','토','일']
TODAY_FULL = f"{now.year}년 {now.month}월 {now.day}일 ({DAYS_KO[now.weekday()]})"
TODAY_YMD  = now.strftime("%Y-%m-%d")
GENERATED_AT = now.strftime("%Y년 %m월 %d일 %H:%M KST")
 
client = anthropic.Anthropic()
 
def call_claude(prompt):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    return "".join(b.text for b in response.content if b.type == "text")
 
def safe_json(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text).strip()
    s, e = text.find('{'), text.rfind('}')
    if s >= 0 and e >= 0:
        try: return json.loads(text[s:e+1])
        except: pass
    return {}
 
# ── 1차 호출: 시장 지표 + 뉴스 ──
print("📡 [1/2] 시장 데이터 + 뉴스 수집 중...")
raw1 = call_claude(f"""오늘({TODAY_YMD}) 웹검색으로 한국/미국 증시 데이터와 뉴스를 수집해 JSON으로만 반환:
{{"kospi":{"close":"","chg":""},"kosdaq":{"close":"","chg":""},"usd_krw":"","sp500":{"close":"","chg":""},"nasdaq":{"close":"","chg":""},"dow":{"close":"","chg":""},"wti":"","us10y":"","prev_label":"전일 날짜(예:5/27화)","banner":"전거래일 결과 한줄요약","news":[{{"type":"bull","tag":"","title":"","desc":""}},{{"type":"warn","tag":"","title":"","desc":""}},{{"type":"neutral","tag":"","title":"","desc":""}}],"schedule":[{{"date":"","today":false,"title":"","desc":"","imp":"high"}}],"futures":[{{"name":"S&P500","val":"","chg":"","cls":"up"}},{{"name":"나스닥","val":"","chg":"","cls":"up"}},{{"name":"다우","val":"","chg":"","cls":"up"}},{{"name":"필라델피아반도체","val":"","chg":"","cls":"up"}},{{"name":"WTI","val":"","chg":"","cls":"up"}},{{"name":"미10년물","val":"","chg":"","cls":"neutral"}},{{"name":"원/달러","val":"","chg":"","cls":"up"}},{{"name":"코스피200선물","val":"","chg":"","cls":"neutral"}}]}}""")
d1 = safe_json(raw1)
print(f"  코스피: {d1.get('kospi',{}).get('close','—')}")
 
time.sleep(65)
 
# ── 2차 호출: 분석 ──
print("🧠 [2/2] AI 분석 생성 중...")
raw2 = call_claude(f"""오늘({TODAY_YMD}) 코스피={d1.get('kospi',{}).get('close','')}, S&P500={d1.get('sp500',{}).get('close','')} 기준으로 분석해 JSON으로만 반환:
{{"sentiment":"","sentiment_reason":"","kospi_up":55,"kospi_neutral":15,"kosdaq_up":58,"kosdaq_neutral":14,"kospi_badge":"","kosdaq_badge":"","kospi_pred":{{"bear":"","bp":30,"base":"","bap":50,"bull":"","bup":20}},"kosdaq_pred":{{"bear":"","bp":25,"base":"","bap":55,"bull":"","bup":20}},"kospi_base":0,"kosdaq_base":0,"sectors":[{{"name":"반도체","chg":1.5,"note":""}},{{"name":"2차전지","chg":0.8,"note":""}},{{"name":"바이오","chg":0.5,"note":""}},{{"name":"항공여행","chg":0.3,"note":""}},{{"name":"금융","chg":-0.2,"note":""}},{{"name":"건설","chg":-0.5,"note":""}},{{"name":"유틸리티","chg":-0.8,"note":""}}],"analysis":"2-3문단 종합분석","tags":[{{"type":"bull","text":""}},{{"type":"warn","text":""}},{{"type":"bear","text":""}}]}}""")
d2 = safe_json(raw2)
print(f"  센티먼트: {d2.get('sentiment','—')}")
 
# ── HTML 생성 ──
m  = d1
kp = d2.get('kospi_pred', {})
kdp= d2.get('kosdaq_pred',{})
k_up  = d2.get('kospi_up', 55)
k_n   = d2.get('kospi_neutral', 15)
kd_up = d2.get('kosdaq_up', 58)
kd_n  = d2.get('kosdaq_neutral', 14)
 
def prob_rows(up, neu):
    dn = 100-up-neu
    return f"""<div class="prob-row"><span class="prob-name up">추가 상승</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:{up}%;background:linear-gradient(90deg,#ef4444,#dc2626);"><span style="font-size:10px;font-weight:700;color:#fff;">{up}%</span></div></div><span class="prob-pct up">{up}%</span></div>
<div class="prob-row"><span class="prob-name neutral">횡보</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:{neu}%;background:#9ca3af;"><span style="font-size:10px;font-weight:700;color:#fff;">{neu}%</span></div></div><span class="prob-pct neutral">{neu}%</span></div>
<div class="prob-row"><span class="prob-name down">하락</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:{dn}%;background:linear-gradient(90deg,#3b82f6,#2563eb);"><span style="font-size:10px;font-weight:700;color:#fff;">{dn}%</span></div></div><span class="prob-pct down">{dn}%</span></div>"""
 
def news_html(lst):
    r=""
    for n in (lst or [])[:3]:
        t=n.get("type","neutral"); cls="bull" if t=="bull" else("warn" if t=="warn" else "")
        r+=f'<div class="news-item {cls}"><div class="news-tag">{n.get("tag","")}</div><div class="news-title">{n.get("title","")}</div><div class="news-desc">{n.get("desc","")}</div></div>'
    return r
 
def sched_html(lst):
    r=""
    for s in (lst or [])[:5]:
        ic="sch-high" if s.get("imp")=="high" else "sch-med"; it="주요" if s.get("imp")=="high" else "중요"
        td="<br>오늘" if s.get("today") else ""
        r+=f'<div class="schedule-row"><span class="sch-date">{s.get("date","")}{td}</span><div class="sch-content"><div class="sch-title">{s.get("title","")} <span class="sch-badge {ic}">{it}</span></div><div class="sch-desc">{s.get("desc","")}</div></div></div>'
    return r
 
def futures_html(lst):
    r=""
    for f in (lst or []):
        r+=f'<div class="futures-item"><div class="futures-name">{f.get("name","")}</div><div class="futures-val {f.get("cls","")}">{f.get("val","—")}</div><div class="futures-chg {f.get("cls","")}">{f.get("chg","")}</div></div>'
    return r
 
def sectors_html(lst):
    if not lst: return ""
    mx=max(abs(s.get("chg",0)) for s in lst) or 1; r=""
    for s in lst:
        c=s.get("chg",0); pct=abs(c)/mx*100; col="#dc2626" if c>=0 else "#2563eb"; cls="up" if c>=0 else "down"; sg="+" if c>=0 else ""
        r+=f'<div class="sector-row"><span class="sector-name">{s.get("name","")}</span><div class="sector-bar-bg"><div class="sector-bar" style="width:{pct:.0f}%;background:{col};"></div></div><span class="sector-pct {cls}">{sg}{c:.1f}%</span></div>'
    return r
 
def tags_html(lst):
    return "".join(f'<span class="tag tag-{t.get("type","neutral")}">{t.get("text","")}</span>' for t in (lst or []))
 
def pred_html(p):
    return f'<div class="pred-item pred-bear"><div class="pred-label">약세</div><div class="pred-range down">{p.get("bear","—")}</div><div class="pred-prob">{p.get("bp","—")}%</div></div><div class="pred-item pred-base"><div class="pred-label">기본</div><div class="pred-range">{p.get("base","—")}</div><div class="pred-prob">{p.get("bap","—")}%</div></div><div class="pred-item pred-bull"><div class="pred-label">강세</div><div class="pred-range up">{p.get("bull","—")}</div><div class="pred-prob">{p.get("bup","—")}%</div></div>'
 
def gen_lines(base, pred):
    bull_str=pred.get("bull",""); bear_str=pred.get("bear","")
    nb=re.findall(r'[\d]+\.?\d*', bull_str.replace(',','')); nd=re.findall(r'[\d]+\.?\d*', bear_str.replace(',',''))
    bh=float(nb[-1]) if nb else base*1.012; bl=float(nd[0]) if nd else base*0.988
    n=13
    hi=[round(base+(bh-base)*(i/(n-1)),2) for i in range(n)]
    lo=[round(base+(bl-base)*(i/(n-1)),2) for i in range(n)]
    ba=[(h+l)/2 for h,l in zip(hi,lo)]
    return ba,hi,lo
 
kb,kh,kl=gen_lines(d2.get('kospi_base',7800), kp)
kdb,kdh,kdl=gen_lines(d2.get('kosdaq_base',1100), kdp)
 
kospi  = m.get('kospi',{})
kosdaq = m.get('kosdaq',{})
sp500  = m.get('sp500',{})
nasdaq = m.get('nasdaq',{})
dow    = m.get('dow',{})
 
HTML = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>한국 주식시장 AI 대시보드 | {TODAY_FULL}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif;background:#f0f3f8;color:#1a1a2e;font-size:14px}}
.container{{max-width:1200px;margin:0 auto;padding:20px}}
.mw-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px}}
.mw-logo-box{{background:#E8380D;border-radius:4px;padding:5px 12px}}
.mw-logo-text{{font-size:13px;font-weight:500;color:#fff;letter-spacing:.02em}}
.mw-logo-sub{{font-size:11px;color:#666;margin-left:8px}}
.mw-date-area{{display:flex;align-items:center;gap:8px}}
.mw-date{{font-size:12px;color:#666}}
.mw-live{{display:flex;align-items:center;gap:4px;font-size:11px;font-weight:600;color:#E8380D;background:#fdf0ed;border:.5px solid #f5b8a8;border-radius:99px;padding:2px 10px}}
.mw-main{{border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1);margin-bottom:16px}}
.mw-header-bar{{background:#043B72;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
.mw-title-en{{font-size:10px;font-weight:500;letter-spacing:.14em;color:rgba(255,255,255,.5);text-transform:uppercase;margin-bottom:5px}}
.mw-title-ko{{font-size:22px;font-weight:500;color:#fff;letter-spacing:-.02em}}
.mw-title-ko em{{color:#F58220;font-style:normal}}
.mw-title-desc{{font-size:12px;color:rgba(255,255,255,.5);margin-top:4px}}
.mw-header-right{{display:flex;flex-direction:column;align-items:flex-end;gap:8px}}
.mw-sentiment-chip{{display:flex;align-items:center;gap:7px;background:rgba(255,255,255,.1);border:.5px solid rgba(255,255,255,.2);border-radius:99px;padding:5px 14px}}
.mw-s-dot{{width:7px;height:7px;border-radius:50%;background:#4ade80}}
.mw-s-label{{font-size:11px;color:rgba(255,255,255,.65)}}
.mw-s-val{{font-size:12px;font-weight:600;color:#fff}}
.mw-kpi-row{{display:flex;align-items:center;gap:12px}}
.mw-kpi{{text-align:right}}
.mw-kpi-val{{font-size:16px;font-weight:600;color:#fca5a5}}
.mw-kpi-label{{font-size:10px;color:rgba(255,255,255,.5);margin-top:1px}}
.mw-kpi-div{{width:.5px;height:32px;background:rgba(255,255,255,.2)}}
.mw-bottom-bar{{background:#f8f9fc;padding:9px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;border-top:1px solid #e5e7eb}}
.mw-sources{{display:flex;align-items:center;gap:6px}}
.mw-src-label{{font-size:11px;color:#888}}
.mw-pill{{font-size:10px;padding:2px 8px;border-radius:99px;border:.5px solid #d1d5db;color:#666;background:#fff}}
.mw-update{{font-size:11px;color:#888}}
.mw-orange-line{{height:3px;background:#F58220}}
.result-banner{{background:linear-gradient(135deg,#043B72,#1d5fa8);border-radius:12px;padding:14px 20px;margin-bottom:14px;box-shadow:0 2px 8px rgba(4,59,114,.2)}}
.result-banner h3{{font-size:12px;font-weight:600;color:rgba(255,255,255,.7);margin-bottom:10px}}
.result-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.result-item{{text-align:center}}
.result-label{{font-size:10px;color:rgba(255,255,255,.6);margin-bottom:3px}}
.result-val{{font-size:17px;font-weight:700;color:#fca5a5}}
.result-chg{{font-size:11px;color:rgba(255,255,255,.75);margin-top:2px}}
.news-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}}
.news-item{{background:#fff;border-radius:10px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,.07);border-left:3px solid #2563eb}}
.news-item.bull{{border-left-color:#dc2626}}.news-item.warn{{border-left-color:#d97706}}
.news-tag{{font-size:10px;font-weight:700;color:#2563eb;margin-bottom:4px}}
.news-item.bull .news-tag{{color:#dc2626}}.news-item.warn .news-tag{{color:#d97706}}
.news-title{{font-size:12px;font-weight:600;margin-bottom:3px;line-height:1.5}}
.news-desc{{font-size:11px;color:#666;line-height:1.5}}
.grid-4{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}}
.metric-card{{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
.metric-label{{font-size:11px;color:#888;margin-bottom:4px}}
.metric-value{{font-size:22px;font-weight:700}}
.metric-sub{{font-size:12px;margin-top:3px}}
.card{{background:#fff;border-radius:12px;padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
.card-title{{font-size:13px;font-weight:600;color:#444;margin-bottom:12px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.up{{color:#dc2626}}.down{{color:#2563eb}}.neutral{{color:#888}}.warnc{{color:#d97706}}
.badge{{font-size:10px;padding:2px 8px;border-radius:99px;font-weight:600}}
.badge-warn{{background:#fef3c7;color:#92400e}}.badge-green{{background:#d1fae5;color:#065f46}}
.gauge-wrap{{margin-bottom:10px}}
.gauge-bar-outer{{width:100%;height:28px;border-radius:14px;overflow:hidden;display:flex;position:relative;background:#e5e7eb;margin-bottom:5px}}
.gauge-up-fill{{height:100%;display:flex;align-items:center;justify-content:center}}
.gauge-down-fill{{height:100%;flex:1;display:flex;align-items:center;justify-content:center}}
.gauge-bar-label{{font-size:11px;font-weight:700;color:#fff}}
.gauge-center-line{{position:absolute;left:50%;top:0;bottom:0;width:2px;background:rgba(255,255,255,.5)}}
.gauge-labels{{display:flex;justify-content:space-between;font-size:11px;font-weight:600}}
.gauge-label-up{{color:#dc2626}}.gauge-label-center{{color:#999}}.gauge-label-down{{color:#2563eb}}
.prob-divider{{text-align:center;font-size:10px;color:#999;margin:6px 0}}
.prob-row{{display:flex;align-items:center;gap:8px;margin-bottom:7px}}
.prob-row:last-child{{margin-bottom:0}}
.prob-name{{font-size:11px;font-weight:600;width:56px;flex-shrink:0}}
.prob-bar-bg{{flex:1;height:18px;border-radius:9px;overflow:hidden;background:#e5e7eb}}
.prob-bar-inner{{height:100%;border-radius:9px;display:flex;align-items:center;justify-content:flex-end;padding-right:7px}}
.prob-pct{{font-size:13px;font-weight:700;width:34px;text-align:right;flex-shrink:0}}
.pred-band{{display:flex;gap:6px;margin-bottom:10px}}
.pred-item{{flex:1;padding:7px 8px;border-radius:8px;text-align:center}}
.pred-bear{{background:#eff6ff}}.pred-base{{background:#f9fafb}}.pred-bull{{background:#fef2f2}}
.pred-label{{font-size:10px;color:#888;margin-bottom:3px}}
.pred-range{{font-size:12px;font-weight:700}}
.pred-prob{{font-size:10px;color:#888;margin-top:2px}}
.futures-grid{{display:grid;grid-template-columns:1fr 1fr;gap:7px}}
.futures-item{{padding:8px 10px;background:#f9fafb;border-radius:8px}}
.futures-name{{font-size:10px;color:#888;margin-bottom:2px}}
.futures-val{{font-size:14px;font-weight:700}}
.futures-chg{{font-size:11px}}
.sector-row{{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #f0f0f0}}
.sector-row:last-child{{border-bottom:none}}
.sector-name{{width:82px;font-size:11px;flex-shrink:0;font-weight:500}}
.sector-bar-bg{{flex:1;height:5px;background:#f0f0f0;border-radius:3px;overflow:hidden}}
.sector-bar{{height:100%;border-radius:3px}}
.sector-pct{{width:44px;text-align:right;font-size:11px;font-weight:700;flex-shrink:0}}
.schedule-row{{display:flex;align-items:flex-start;gap:10px;padding:7px 0;border-bottom:1px solid #f0f0f0}}
.schedule-row:last-child{{border-bottom:none}}
.sch-date{{font-size:11px;font-weight:700;width:36px;flex-shrink:0;color:#043B72}}
.sch-content{{flex:1}}
.sch-title{{font-size:12px;font-weight:600}}
.sch-desc{{font-size:11px;color:#666;margin-top:2px}}
.sch-badge{{font-size:10px;padding:1px 7px;border-radius:99px;font-weight:600;margin-left:5px}}
.sch-high{{background:#fee2e2;color:#b91c1c}}.sch-med{{background:#fef3c7;color:#92400e}}
.analysis-text{{font-size:13px;line-height:1.8;color:#333}}
.tags{{margin-top:10px}}
.tag{{display:inline-block;font-size:11px;padding:2px 9px;border-radius:99px;margin:2px 3px 2px 0}}
.tag-bull{{background:#fee2e2;color:#b91c1c}}.tag-bear{{background:#dbeafe;color:#1d4ed8}}
.tag-neutral{{background:#f3f4f6;color:#555}}.tag-warn{{background:#fef3c7;color:#92400e}}
.tag-purple{{background:#ede9fe;color:#5b21b6}}
.notice{{font-size:11px;color:#999;background:#f9fafb;border-radius:8px;padding:9px 12px;margin-top:12px;border:1px solid #e5e7eb}}
.chart-wrap{{position:relative;height:165px}}
.footer{{text-align:center;margin-top:20px;font-size:11px;color:#bbb;padding-bottom:16px}}
@media(max-width:768px){{.grid-4{{grid-template-columns:repeat(2,1fr)}}.grid-2{{grid-template-columns:1fr}}.news-row{{grid-template-columns:1fr}}.result-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="container">
  <div class="mw-top">
    <div style="display:flex;align-items:center;gap:8px;">
      <div class="mw-logo-box"><span class="mw-logo-text">MIRAE ASSET</span></div>
      <span class="mw-logo-sub">Market Intelligence</span>
    </div>
    <div class="mw-date-area">
      <span class="mw-date">{TODAY_FULL}</span>
      <span class="mw-live">● AI 생성</span>
    </div>
  </div>
  <div class="mw-main">
    <div class="mw-header-bar">
      <div>
        <div class="mw-title-en">Korea Equity Market AI Dashboard</div>
        <div class="mw-title-ko">한국 주식시장 <em>AI</em> 대시보드</div>
        <div class="mw-title-desc">전일 미국 증시 · 야간선물 · 환율 · 주요 경제 뉴스 종합 분석</div>
      </div>
      <div class="mw-header-right">
        <div class="mw-sentiment-chip">
          <div class="mw-s-dot"></div>
          <span class="mw-s-label">오늘 센티먼트</span>
          <span class="mw-s-val">{d2.get('sentiment','—')}</span>
        </div>
        <div class="mw-kpi-row">
          <div class="mw-kpi"><div class="mw-kpi-val">{kospi.get('close','—')}</div><div class="mw-kpi-label">코스피 전일({m.get('prev_label','—')})</div></div>
          <div class="mw-kpi-div"></div>
          <div class="mw-kpi"><div class="mw-kpi-val">{kospi.get('chg','—')}</div><div class="mw-kpi-label">전일 등락</div></div>
          <div class="mw-kpi-div"></div>
          <div class="mw-kpi"><div class="mw-kpi-val">{kosdaq.get('close','—')}</div><div class="mw-kpi-label">코스닥 전일</div></div>
        </div>
      </div>
    </div>
    <div class="mw-bottom-bar">
      <div class="mw-sources">
        <span class="mw-src-label">데이터 소스</span>
        <span class="mw-pill">KRX</span><span class="mw-pill">Bloomberg</span><span class="mw-pill">Reuters</span><span class="mw-pill">뉴스검색</span>
      </div>
      <span class="mw-update">AI 생성: {GENERATED_AT}</span>
    </div>
    <div class="mw-orange-line"></div>
  </div>
 
  <div class="result-banner">
    <h3>📌 {m.get('banner','전 거래일 실제 마감 결과')}</h3>
    <div class="result-grid">
      <div class="result-item"><div class="result-label">코스피 종가</div><div class="result-val">{kospi.get('close','—')}</div><div class="result-chg">{kospi.get('chg','—')}</div></div>
      <div class="result-item"><div class="result-label">S&amp;P 500</div><div class="result-val">{sp500.get('close','—')}</div><div class="result-chg">{sp500.get('chg','—')}</div></div>
      <div class="result-item"><div class="result-label">나스닥</div><div class="result-val">{nasdaq.get('close','—')}</div><div class="result-chg">{nasdaq.get('chg','—')}</div></div>
      <div class="result-item"><div class="result-label">다우존스</div><div class="result-val">{dow.get('close','—')}</div><div class="result-chg">{dow.get('chg','—')}</div></div>
    </div>
  </div>
 
  <div class="news-row">{news_html(m.get('news',[]))}</div>
 
  <div class="grid-4">
    <div class="metric-card"><div class="metric-label">코스피 전일 종가</div><div class="metric-value up">{kospi.get('close','—')}</div><div class="metric-sub up">{kospi.get('chg','—')}</div></div>
    <div class="metric-card"><div class="metric-label">코스닥 전일 종가</div><div class="metric-value up">{kosdaq.get('close','—')}</div><div class="metric-sub up">{kosdaq.get('chg','—')}</div></div>
    <div class="metric-card"><div class="metric-label">오늘 시장 센티먼트</div><div class="metric-value warnc">{d2.get('sentiment','—')}</div><div class="metric-sub warnc">{d2.get('sentiment_reason','')}</div></div>
    <div class="metric-card"><div class="metric-label">원/달러 환율</div><div class="metric-value up">{m.get('usd_krw','—')}</div><div class="metric-sub up">오늘 예상</div></div>
  </div>
 
  <div class="grid-2">
    <div class="card">
      <div class="card-title">📊 코스피 상승/하락 확률 <span class="badge badge-warn">{d2.get('kospi_badge','')}</span></div>
      <div class="gauge-wrap">
        <div class="gauge-bar-outer">
          <div class="gauge-up-fill" style="width:{k_up}%;background:linear-gradient(90deg,#fca5a5,#dc2626);"><span class="gauge-bar-label">{k_up}%</span></div>
          <div class="gauge-down-fill" style="background:linear-gradient(90deg,#93c5fd,#2563eb);"><span class="gauge-bar-label">{100-k_up}%</span></div>
          <div class="gauge-center-line"></div>
        </div>
        <div class="gauge-labels"><span class="gauge-label-up">▲ 상승 {k_up}%</span><span class="gauge-label-center">50%</span><span class="gauge-label-down">하락 {100-k_up}% ▼</span></div>
      </div>
      <div class="prob-divider">— 시나리오별 확률 —</div>
      {prob_rows(k_up, k_n)}
    </div>
    <div class="card">
      <div class="card-title">📊 코스닥 상승/하락 확률 <span class="badge badge-green">{d2.get('kosdaq_badge','')}</span></div>
      <div class="gauge-wrap">
        <div class="gauge-bar-outer">
          <div class="gauge-up-fill" style="width:{kd_up}%;background:linear-gradient(90deg,#fca5a5,#dc2626);"><span class="gauge-bar-label">{kd_up}%</span></div>
          <div class="gauge-down-fill" style="background:linear-gradient(90deg,#93c5fd,#2563eb);"><span class="gauge-bar-label">{100-kd_up}%</span></div>
          <div class="gauge-center-line"></div>
        </div>
        <div class="gauge-labels"><span class="gauge-label-up">▲ 상승 {kd_up}%</span><span class="gauge-label-center">50%</span><span class="gauge-label-down">하락 {100-kd_up}% ▼</span></div>
      </div>
      <div class="prob-divider">— 시나리오별 확률 —</div>
      {prob_rows(kd_up, kd_n)}
    </div>
  </div>
 
  <div class="grid-2">
    <div class="card">
      <div class="card-title">📈 코스피 장중 예상 <span class="badge badge-warn">{d2.get('kospi_badge','')}</span></div>
      <div class="pred-band">{pred_html(kp)}</div>
      <div class="chart-wrap"><canvas id="kospiChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">📈 코스닥 장중 예상 <span class="badge badge-green">{d2.get('kosdaq_badge','')}</span></div>
      <div class="pred-band">{pred_html(kdp)}</div>
      <div class="chart-wrap"><canvas id="kosdaqChart"></canvas></div>
    </div>
  </div>
 
  <div class="grid-2">
    <div class="card">
      <div class="card-title">🌍 전 거래일 미국 증시 &amp; 주요 지표</div>
      <div class="futures-grid">{futures_html(m.get('futures',[]))}</div>
    </div>
    <div class="card">
      <div class="card-title">📅 이번 주 주요 경제 일정</div>
      {sched_html(m.get('schedule',[]))}
    </div>
  </div>
 
  <div class="grid-2">
    <div class="card">
      <div class="card-title">🏦 오늘 업종 예상</div>
      {sectors_html(d2.get('sectors',[]))}
    </div>
    <div class="card">
      <div class="card-title">🧠 AI 종합 분석</div>
      <div class="analysis-text">{d2.get('analysis','분석 중 오류가 발생했습니다.')}</div>
      <div class="tags">{tags_html(d2.get('tags',[]))}</div>
      <div class="notice">⚠️ 본 분석은 공개된 시장 데이터 및 뉴스를 바탕으로 한 참고용 예상이며, 실제 투자 판단의 근거로 사용하지 마세요.</div>
    </div>
  </div>
 
  <div class="footer">MIRAE ASSET Market Intelligence · 한국 주식시장 AI 대시보드 · {TODAY_FULL} · 참고용</div>
</div>
<script>
const L=['9:00','9:30','10:00','10:30','11:00','11:30','12:00','13:00','13:30','14:00','14:30','15:00','15:30'];
function makeChart(id,base,high,low,color){{
  new Chart(document.getElementById(id).getContext('2d'),{{
    type:'line',
    data:{{labels:L,datasets:[
      {{label:'상단',data:high,borderColor:color,borderWidth:1,borderDash:[4,3],fill:false,tension:.4,pointRadius:0}},
      {{label:'기본',data:base,borderColor:color,borderWidth:2.5,fill:false,tension:.4,pointRadius:3,pointBackgroundColor:color}},
      {{label:'하단',data:low,borderColor:color,borderWidth:1,borderDash:[4,3],fill:'-1',backgroundColor:color+'14',tension:.4,pointRadius:0}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{display:false}},tooltip:{{mode:'index',intersect:false}}}},
      scales:{{x:{{grid:{{display:false}},ticks:{{font:{{size:10}},maxRotation:0,maxTicksLimit:7}}}},
               y:{{grid:{{color:'rgba(0,0,0,.04)'}},ticks:{{font:{{size:10}},callback:v=>v.toLocaleString()}}}}}}
    }}
  }});
}}
makeChart('kospiChart',{json.dumps(kb)},{json.dumps(kh)},{json.dumps(kl)},'#dc2626');
makeChart('kosdaqChart',{json.dumps(kdb)},{json.dumps(kdh)},{json.dumps(kdl)},'#2563eb');
</script>
</body>
</html>"""
 
with open("index.html","w",encoding="utf-8") as f:
    f.write(HTML)
print(f"✅ 완료! ({len(HTML):,} bytes)")
