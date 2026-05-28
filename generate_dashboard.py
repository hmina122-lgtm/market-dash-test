#!/usr/bin/env python3
"""
한국 주식시장 AI 대시보드 생성기
매일 GitHub Actions에서 실행되어 index.html을 생성합니다.
"""

import anthropic
import json
import re
from datetime import datetime, timezone, timedelta

# 한국 시간
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
DAYS_KO = ['월','화','수','목','금','토','일']
TODAY_FULL = f"{now.year}년 {now.month}월 {now.day}일 ({DAYS_KO[now.weekday()]})"
TODAY_YMD  = now.strftime("%Y-%m-%d")
GENERATED_AT = now.strftime("%Y년 %m월 %d일 %H:%M KST")

client = anthropic.Anthropic()   # ANTHROPIC_API_KEY 환경변수 자동 사용

SYSTEM = f"""당신은 한국 주식시장 전문 애널리스트입니다.
오늘 날짜: {TODAY_YMD} ({TODAY_FULL})
웹 검색으로 최신 데이터를 수집한 뒤, 반드시 순수 JSON만 반환하세요.
마크다운 코드블록·설명 텍스트 없이 JSON 객체만 출력하세요."""

def call_claude(prompt: str) -> str:
    """Claude API 호출 (웹 검색 포함)"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    return "".join(b.text for b in response.content if b.type == "text")

def safe_json(text: str) -> dict:
    """JSON 안전 파싱"""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    start, end = text.find('{'), text.rfind('}')
    if start >= 0 and end >= 0:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
    return {}

# ──────────────────────────────────────────
# 1. 시장 지표
# ──────────────────────────────────────────
print("📡 [1/4] 시장 지표 수집 중...")
market_raw = call_claude(f"""
오늘({TODAY_YMD}) 기준으로 웹 검색하여 아래 정보를 수집해 JSON으로 반환하세요:
{{
  "kospi_close": "코스피 전일 종가 (예: 2,650.34)",
  "kospi_change": "코스피 전일 등락 (예: +32.12p (+0.41%))",
  "kosdaq_close": "코스닥 전일 종가",
  "kosdaq_change": "코스닥 전일 등락",
  "usd_krw": "원/달러 환율 (예: 1,380원)",
  "sp500": "S&P500 최근 종가",
  "sp500_change": "S&P500 등락",
  "nasdaq": "나스닥 최근 종가",
  "nasdaq_change": "나스닥 등락",
  "dow": "다우존스 최근 종가",
  "dow_change": "다우 등락",
  "wti": "WTI 유가",
  "us_10y": "미 10년물 금리",
  "prev_date_label": "전일 날짜 (예: 5/27 화)",
  "banner_title": "전 거래일 결과 요약 한 줄"
}}""")
market = safe_json(market_raw)
print(f"  코스피: {market.get('kospi_close','—')}, S&P500: {market.get('sp500','—')}")

# ──────────────────────────────────────────
# 2. 뉴스 & 일정
# ──────────────────────────────────────────
print("📰 [2/4] 뉴스·이벤트 수집 중...")
news_raw = call_claude(f"""
오늘({TODAY_YMD}) 한국 주식시장에 영향을 미치는 최신 뉴스를 웹 검색하여 JSON으로 반환하세요:
{{
  "news": [
    {{"type":"bull","tag":"🇺🇸 미국 증시","title":"헤드라인","desc":"2-3문장 요약"}},
    {{"type":"warn","tag":"📅 주요 이벤트","title":"...","desc":"..."}},
    {{"type":"neutral","tag":"⚠️ 주요 리스크","title":"...","desc":"..."}}
  ],
  "schedule": [
    {{"date":"날짜 (예: 5/28 수)","today":true,"title":"이벤트 제목","desc":"설명","importance":"high"}},
    ...최대 5개
  ],
  "us_futures": [
    {{"name":"S&P 500","val":"...","chg":"...","cls":"up"}},
    {{"name":"나스닥","val":"...","chg":"...","cls":"up"}},
    {{"name":"다우존스","val":"...","chg":"...","cls":"up"}},
    {{"name":"필라델피아 반도체","val":"...","chg":"...","cls":"up"}},
    {{"name":"WTI 유가","val":"...","chg":"...","cls":"down"}},
    {{"name":"미 10년물 금리","val":"...","chg":"...","cls":"neutral"}},
    {{"name":"원/달러 (예상)","val":"...","chg":"...","cls":"up"}},
    {{"name":"코스피200 야간선물","val":"...","chg":"...","cls":"neutral"}}
  ]
}}""")
news = safe_json(news_raw)

# ──────────────────────────────────────────
# 3. 확률 분석
# ──────────────────────────────────────────
print("📊 [3/4] 방향성·확률 분석 중...")
prob_raw = call_claude(f"""
오늘({TODAY_YMD}) 수집된 시장 데이터: {json.dumps(market, ensure_ascii=False)}
이를 바탕으로 오늘 코스피·코스닥 방향성을 분석하여 JSON으로 반환하세요:
{{
  "sentiment": "오늘 시장 센티먼트 (예: 중립~소폭 강세)",
  "sentiment_reason": "이유 한 줄",
  "kospi_up_pct": 55,
  "kospi_neutral_pct": 15,
  "kosdaq_up_pct": 58,
  "kosdaq_neutral_pct": 14,
  "kospi_badge": "코스피 핵심 키워드",
  "kosdaq_badge": "코스닥 핵심 키워드",
  "kospi_pred": {{"bear":"범위","bear_prob":30,"base":"범위","base_prob":50,"bull":"범위","bull_prob":20}},
  "kosdaq_pred": {{"bear":"범위","bear_prob":25,"base":"범위","base_prob":55,"bull":"범위","bull_prob":20}},
  "kospi_base_price": 2650,
  "kosdaq_base_price": 850
}}""")
prob = safe_json(prob_raw)

# ──────────────────────────────────────────
# 4. 섹터 & 종합 분석
# ──────────────────────────────────────────
print("🧠 [4/4] 섹터·종합 분석 생성 중...")
analysis_raw = call_claude(f"""
오늘({TODAY_YMD}) 한국 주식시장 업종별 예상 등락과 AI 종합 분석을 JSON으로 반환하세요:
{{
  "sectors": [
    {{"name":"반도체","chg":1.5,"note":"AI Capex 사이클 지속"}},
    {{"name":"2차전지","chg":0.8,"note":"순환매 기대"}},
    {{"name":"바이오·제약","chg":0.5,"note":"코스닥 수급 개선"}},
    {{"name":"항공·여행","chg":0.3,"note":"유가 안정"}},
    {{"name":"금융","chg":-0.2,"note":"금리 변동성"}},
    {{"name":"건설","chg":-0.5,"note":"금리 부담"}},
    {{"name":"유틸리티","chg":-0.8,"note":"LNG 가격 부담"}}
  ],
  "analysis": "2-3문단 AI 종합 분석 (HTML <strong> 태그 사용 가능)",
  "tags": [
    {{"type":"bull","text":"긍정 키워드"}},
    {{"type":"warn","text":"주의 키워드"}},
    {{"type":"bear","text":"리스크 키워드"}}
  ]
}}""")
analysis = safe_json(analysis_raw)

# ──────────────────────────────────────────
# HTML 생성
# ──────────────────────────────────────────
print("🖥️  HTML 생성 중...")

def gauge_prob_rows(up, neutral):
    down = 100 - up - neutral
    return f"""
    <div class="prob-row">
      <span class="prob-name up">추가 상승</span>
      <div class="prob-bar-bg"><div class="prob-bar-inner" style="width:{up}%;background:linear-gradient(90deg,#ef4444,#dc2626);"><span style="font-size:10px;font-weight:700;color:#fff;">{up}%</span></div></div>
      <span class="prob-pct up">{up}%</span>
    </div>
    <div class="prob-row">
      <span class="prob-name neutral">횡보</span>
      <div class="prob-bar-bg"><div class="prob-bar-inner" style="width:{neutral}%;background:#9ca3af;"><span style="font-size:10px;font-weight:700;color:#fff;">{neutral}%</span></div></div>
      <span class="prob-pct neutral">{neutral}%</span>
    </div>
    <div class="prob-row">
      <span class="prob-name down">하락</span>
      <div class="prob-bar-bg"><div class="prob-bar-inner" style="width:{down}%;background:linear-gradient(90deg,#3b82f6,#2563eb);"><span style="font-size:10px;font-weight:700;color:#fff;">{down}%</span></div></div>
      <span class="prob-pct down">{down}%</span>
    </div>"""

def news_items_html(news_list):
    html = ""
    for n in (news_list or [])[:3]:
        t = n.get("type","neutral")
        cls = "bull" if t=="bull" else ("warn" if t=="warn" else "")
        html += f"""<div class="news-item {cls}">
      <div class="news-tag">{n.get('tag','')}</div>
      <div class="news-title">{n.get('title','')}</div>
      <div class="news-desc">{n.get('desc','')}</div>
    </div>"""
    return html

def schedule_html(sched_list):
    html = ""
    for s in (sched_list or [])[:5]:
        imp = s.get("importance","med")
        badge_cls = "sch-high" if imp=="high" else "sch-med"
        badge_txt = "주요" if imp=="high" else "중요"
        today_txt = "<br>오늘" if s.get("today") else ""
        html += f"""<div class="schedule-row">
      <span class="sch-date">{s.get('date','')}{today_txt}</span>
      <div class="sch-content">
        <div class="sch-title">{s.get('title','')} <span class="sch-badge {badge_cls}">{badge_txt}</span></div>
        <div class="sch-desc">{s.get('desc','')}</div>
      </div>
    </div>"""
    return html

def futures_html(futures_list):
    html = ""
    for f in (futures_list or []):
        html += f"""<div class="futures-item">
      <div class="futures-name">{f.get('name','')}</div>
      <div class="futures-val {f.get('cls','')}">{f.get('val','—')}</div>
      <div class="futures-chg {f.get('cls','')}">{f.get('chg','')}</div>
    </div>"""
    return html

def sectors_html(sector_list):
    if not sector_list:
        return ""
    max_abs = max(abs(s.get("chg",0)) for s in sector_list) or 1
    html = ""
    for s in sector_list:
        chg = s.get("chg", 0)
        pct = abs(chg) / max_abs * 100
        col = "#dc2626" if chg >= 0 else "#2563eb"
        cls = "up" if chg >= 0 else "down"
        sign = "+" if chg >= 0 else ""
        html += f"""<div class="sector-row">
      <span class="sector-name">{s.get('name','')}</span>
      <div class="sector-bar-bg"><div class="sector-bar" style="width:{pct:.0f}%;background:{col};"></div></div>
      <span class="sector-pct {cls}">{sign}{chg:.1f}%</span>
    </div>"""
    return html

def tags_html(tag_list):
    html = ""
    for t in (tag_list or []):
        html += f'<span class="tag tag-{t.get("type","neutral")}">{t.get("text","")}</span>'
    return html

def pred_band_html(pred):
    return f"""
    <div class="pred-item pred-bear"><div class="pred-label">약세</div><div class="pred-range down">{pred.get('bear','—')}</div><div class="pred-prob">{pred.get('bear_prob','—')}%</div></div>
    <div class="pred-item pred-base"><div class="pred-label">기본</div><div class="pred-range">{pred.get('base','—')}</div><div class="pred-prob">{pred.get('base_prob','—')}%</div></div>
    <div class="pred-item pred-bull"><div class="pred-label">강세</div><div class="pred-range up">{pred.get('bull','—')}</div><div class="pred-prob">{pred.get('bull_prob','—')}%</div></div>"""

# 차트 데이터 생성
def gen_chart_data(base_price, pred):
    import math
    bear_str = pred.get("bear", "")
    bull_str  = pred.get("bull", "")
    nums_bear = re.findall(r'[\d,]+\.?\d*', bear_str.replace(',',''))
    nums_bull  = re.findall(r'[\d,]+\.?\d*', bull_str.replace(',',''))
    bear_low  = float(nums_bear[0]) if nums_bear else base_price * 0.988
    bull_high = float(nums_bull[-1]) if nums_bull else base_price * 1.012
    n = 13
    base_line = [round(base_price + (bull_high - base_price) * 0.35 * (i/(n-1)), 2) for i in range(n)]
    high_line = [round(base_price + (bull_high - base_price) * (i/(n-1)), 2) for i in range(n)]
    low_line  = [round(base_price + (bear_low - base_price) * (i/(n-1)), 2) for i in range(n)]
    return base_line, high_line, low_line

k_base_price  = prob.get("kospi_base_price", 2650)
kd_base_price = prob.get("kosdaq_base_price", 850)
k_pred  = prob.get("kospi_pred", {})
kd_pred = prob.get("kosdaq_pred", {})
k_base, k_high, k_low   = gen_chart_data(k_base_price, k_pred)
kd_base, kd_high, kd_low = gen_chart_data(kd_base_price, kd_pred)

k_up  = prob.get("kospi_up_pct", 55)
k_n   = prob.get("kospi_neutral_pct", 15)
kd_up = prob.get("kosdaq_up_pct", 58)
kd_n  = prob.get("kosdaq_neutral_pct", 14)

HTML = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>한국 주식시장 AI 대시보드 | {TODAY_FULL}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif; background: #f0f3f8; color: #1a1a2e; font-size: 14px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
  .mw-top {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; flex-wrap: wrap; gap: 8px; }}
  .mw-logo-box {{ background: #E8380D; border-radius: 4px; padding: 5px 12px; }}
  .mw-logo-text {{ font-size: 13px; font-weight: 500; color: #fff; letter-spacing: 0.02em; }}
  .mw-logo-sub {{ font-size: 11px; color: #666; margin-left: 8px; }}
  .mw-date-area {{ display: flex; align-items: center; gap: 8px; }}
  .mw-date {{ font-size: 12px; color: #666; }}
  .mw-live {{ display: flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; color: #E8380D; background: #fdf0ed; border: 0.5px solid #f5b8a8; border-radius: 99px; padding: 2px 10px; }}
  .mw-main {{ border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.1); margin-bottom: 16px; }}
  .mw-header-bar {{ background: #043B72; padding: 18px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
  .mw-title-en {{ font-size: 10px; font-weight: 500; letter-spacing: 0.14em; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 5px; }}
  .mw-title-ko {{ font-size: 22px; font-weight: 500; color: #fff; letter-spacing: -0.02em; }}
  .mw-title-ko em {{ color: #F58220; font-style: normal; }}
  .mw-title-desc {{ font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 4px; }}
  .mw-header-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }}
  .mw-sentiment-chip {{ display: flex; align-items: center; gap: 7px; background: rgba(255,255,255,0.1); border: 0.5px solid rgba(255,255,255,0.2); border-radius: 99px; padding: 5px 14px; }}
  .mw-s-dot {{ width: 7px; height: 7px; border-radius: 50%; background: #4ade80; }}
  .mw-s-label {{ font-size: 11px; color: rgba(255,255,255,0.65); }}
  .mw-s-val {{ font-size: 12px; font-weight: 600; color: #fff; }}
  .mw-kpi-row {{ display: flex; align-items: center; gap: 12px; }}
  .mw-kpi {{ text-align: right; }}
  .mw-kpi-val {{ font-size: 16px; font-weight: 600; color: #fca5a5; }}
  .mw-kpi-label {{ font-size: 10px; color: rgba(255,255,255,0.5); margin-top: 1px; }}
  .mw-kpi-div {{ width: 0.5px; height: 32px; background: rgba(255,255,255,0.2); }}
  .mw-bottom-bar {{ background: #f8f9fc; padding: 9px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; border-top: 1px solid #e5e7eb; }}
  .mw-sources {{ display: flex; align-items: center; gap: 6px; }}
  .mw-src-label {{ font-size: 11px; color: #888; }}
  .mw-pill {{ font-size: 10px; padding: 2px 8px; border-radius: 99px; border: 0.5px solid #d1d5db; color: #666; background: #fff; }}
  .mw-update {{ font-size: 11px; color: #888; }}
  .mw-orange-line {{ height: 3px; background: #F58220; }}
  .result-banner {{ background: linear-gradient(135deg, #043B72 0%, #1d5fa8 100%); border-radius: 12px; padding: 14px 20px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(4,59,114,0.2); }}
  .result-banner h3 {{ font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.7); margin-bottom: 10px; }}
  .result-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .result-item {{ text-align: center; }}
  .result-label {{ font-size: 10px; color: rgba(255,255,255,0.6); margin-bottom: 3px; }}
  .result-val {{ font-size: 17px; font-weight: 700; color: #fca5a5; }}
  .result-chg {{ font-size: 11px; color: rgba(255,255,255,0.75); margin-top: 2px; }}
  .news-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }}
  .news-item {{ background: #fff; border-radius: 10px; padding: 12px 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); border-left: 3px solid #2563eb; }}
  .news-item.bull {{ border-left-color: #dc2626; }}
  .news-item.warn {{ border-left-color: #d97706; }}
  .news-tag {{ font-size: 10px; font-weight: 700; color: #2563eb; margin-bottom: 4px; }}
  .news-item.bull .news-tag {{ color: #dc2626; }}
  .news-item.warn .news-tag {{ color: #d97706; }}
  .news-title {{ font-size: 12px; font-weight: 600; margin-bottom: 3px; line-height: 1.5; }}
  .news-desc {{ font-size: 11px; color: #666; line-height: 1.5; }}
  .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }}
  .metric-card {{ background: #fff; border-radius: 10px; padding: 14px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }}
  .metric-label {{ font-size: 11px; color: #888; margin-bottom: 4px; }}
  .metric-value {{ font-size: 22px; font-weight: 700; }}
  .metric-sub {{ font-size: 12px; margin-top: 3px; }}
  .card {{ background: #fff; border-radius: 12px; padding: 16px 18px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }}
  .card-title {{ font-size: 13px; font-weight: 600; color: #444; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
  .up {{ color: #dc2626; }} .down {{ color: #2563eb; }} .neutral {{ color: #888; }} .warn-c {{ color: #d97706; }}
  .badge {{ font-size: 10px; padding: 2px 8px; border-radius: 99px; font-weight: 600; }}
  .badge-warn {{ background: #fef3c7; color: #92400e; }}
  .badge-green {{ background: #d1fae5; color: #065f46; }}
  .gauge-wrap {{ margin-bottom: 10px; }}
  .gauge-bar-outer {{ width: 100%; height: 28px; border-radius: 14px; overflow: hidden; display: flex; position: relative; background: #e5e7eb; margin-bottom: 5px; }}
  .gauge-up-fill {{ height: 100%; display: flex; align-items: center; justify-content: center; }}
  .gauge-down-fill {{ height: 100%; flex: 1; display: flex; align-items: center; justify-content: center; }}
  .gauge-bar-label {{ font-size: 11px; font-weight: 700; color: #fff; }}
  .gauge-center-line {{ position: absolute; left: 50%; top: 0; bottom: 0; width: 2px; background: rgba(255,255,255,0.5); }}
  .gauge-labels {{ display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; }}
  .gauge-label-up {{ color: #dc2626; }} .gauge-label-center {{ color: #999; }} .gauge-label-down {{ color: #2563eb; }}
  .prob-divider {{ text-align: center; font-size: 10px; color: #999; margin: 6px 0; }}
  .prob-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }}
  .prob-row:last-child {{ margin-bottom: 0; }}
  .prob-name {{ font-size: 11px; font-weight: 600; width: 56px; flex-shrink: 0; }}
  .prob-bar-bg {{ flex: 1; height: 18px; border-radius: 9px; overflow: hidden; background: #e5e7eb; }}
  .prob-bar-inner {{ height: 100%; border-radius: 9px; display: flex; align-items: center; justify-content: flex-end; padding-right: 7px; }}
  .prob-pct {{ font-size: 13px; font-weight: 700; width: 34px; text-align: right; flex-shrink: 0; }}
  .pred-band {{ display: flex; gap: 6px; margin-bottom: 10px; }}
  .pred-item {{ flex: 1; padding: 7px 8px; border-radius: 8px; text-align: center; }}
  .pred-bear {{ background: #eff6ff; }} .pred-base {{ background: #f9fafb; }} .pred-bull {{ background: #fef2f2; }}
  .pred-label {{ font-size: 10px; color: #888; margin-bottom: 3px; }}
  .pred-range {{ font-size: 12px; font-weight: 700; }}
  .pred-prob {{ font-size: 10px; color: #888; margin-top: 2px; }}
  .futures-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }}
  .futures-item {{ padding: 8px 10px; background: #f9fafb; border-radius: 8px; }}
  .futures-name {{ font-size: 10px; color: #888; margin-bottom: 2px; }}
  .futures-val {{ font-size: 14px; font-weight: 700; }}
  .futures-chg {{ font-size: 11px; }}
  .sector-row {{ display: flex; align-items: center; gap: 8px; padding: 5px 0; border-bottom: 1px solid #f0f0f0; }}
  .sector-row:last-child {{ border-bottom: none; }}
  .sector-name {{ width: 82px; font-size: 11px; flex-shrink: 0; font-weight: 500; }}
  .sector-bar-bg {{ flex: 1; height: 5px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }}
  .sector-bar {{ height: 100%; border-radius: 3px; }}
  .sector-pct {{ width: 44px; text-align: right; font-size: 11px; font-weight: 700; flex-shrink: 0; }}
  .schedule-row {{ display: flex; align-items: flex-start; gap: 10px; padding: 7px 0; border-bottom: 1px solid #f0f0f0; }}
  .schedule-row:last-child {{ border-bottom: none; }}
  .sch-date {{ font-size: 11px; font-weight: 700; width: 36px; flex-shrink: 0; color: #043B72; }}
  .sch-content {{ flex: 1; }}
  .sch-title {{ font-size: 12px; font-weight: 600; }}
  .sch-desc {{ font-size: 11px; color: #666; margin-top: 2px; }}
  .sch-badge {{ font-size: 10px; padding: 1px 7px; border-radius: 99px; font-weight: 600; margin-left: 5px; }}
  .sch-high {{ background: #fee2e2; color: #b91c1c; }}
  .sch-med {{ background: #fef3c7; color: #92400e; }}
  .analysis-text {{ font-size: 13px; line-height: 1.8; color: #333; }}
  .tags {{ margin-top: 10px; }}
  .tag {{ display: inline-block; font-size: 11px; padding: 2px 9px; border-radius: 99px; margin: 2px 3px 2px 0; }}
  .tag-bull {{ background: #fee2e2; color: #b91c1c; }}
  .tag-bear {{ background: #dbeafe; color: #1d4ed8; }}
  .tag-neutral {{ background: #f3f4f6; color: #555; }}
  .tag-warn {{ background: #fef3c7; color: #92400e; }}
  .tag-purple {{ background: #ede9fe; color: #5b21b6; }}
  .notice {{ font-size: 11px; color: #999; background: #f9fafb; border-radius: 8px; padding: 9px 12px; margin-top: 12px; border: 1px solid #e5e7eb; }}
  .chart-wrap {{ position: relative; height: 165px; }}
  .footer {{ text-align: center; margin-top: 20px; font-size: 11px; color: #bbb; padding-bottom: 16px; }}
  @media(max-width:768px) {{
    .grid-4 {{ grid-template-columns: repeat(2,1fr); }}
    .grid-2 {{ grid-template-columns: 1fr; }}
    .news-row {{ grid-template-columns: 1fr; }}
    .result-grid {{ grid-template-columns: repeat(2,1fr); }}
  }}
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
          <span class="mw-s-val">{prob.get('sentiment','—')}</span>
        </div>
        <div class="mw-kpi-row">
          <div class="mw-kpi"><div class="mw-kpi-val">{market.get('kospi_close','—')}</div><div class="mw-kpi-label">코스피 전일({market.get('prev_date_label','—')})</div></div>
          <div class="mw-kpi-div"></div>
          <div class="mw-kpi"><div class="mw-kpi-val">{market.get('kospi_change','—')}</div><div class="mw-kpi-label">전일 등락</div></div>
          <div class="mw-kpi-div"></div>
          <div class="mw-kpi"><div class="mw-kpi-val">{market.get('kosdaq_close','—')}</div><div class="mw-kpi-label">코스닥 전일</div></div>
        </div>
      </div>
    </div>
    <div class="mw-bottom-bar">
      <div class="mw-sources">
        <span class="mw-src-label">데이터 소스</span>
        <span class="mw-pill">KRX</span><span class="mw-pill">Bloomberg</span>
        <span class="mw-pill">Reuters</span><span class="mw-pill">뉴스 검색</span><span class="mw-pill">야간선물</span>
      </div>
      <span class="mw-update">AI 생성: {GENERATED_AT}</span>
    </div>
    <div class="mw-orange-line"></div>
  </div>

  <div class="result-banner">
    <h3>📌 {market.get('banner_title', '전 거래일 실제 마감 결과')}</h3>
    <div class="result-grid">
      <div class="result-item"><div class="result-label">코스피 종가</div><div class="result-val">{market.get('kospi_close','—')}</div><div class="result-chg">{market.get('kospi_change','—')}</div></div>
      <div class="result-item"><div class="result-label">S&amp;P 500</div><div class="result-val">{market.get('sp500','—')}</div><div class="result-chg">{market.get('sp500_change','—')}</div></div>
      <div class="result-item"><div class="result-label">나스닥</div><div class="result-val">{market.get('nasdaq','—')}</div><div class="result-chg">{market.get('nasdaq_change','—')}</div></div>
      <div class="result-item"><div class="result-label">다우존스</div><div class="result-val">{market.get('dow','—')}</div><div class="result-chg">{market.get('dow_change','—')}</div></div>
    </div>
  </div>

  <div class="news-row">{news_items_html(news.get('news',[]))}</div>

  <div class="grid-4">
    <div class="metric-card"><div class="metric-label">코스피 전일 종가 ({market.get('prev_date_label','—')})</div><div class="metric-value up">{market.get('kospi_close','—')}</div><div class="metric-sub up">{market.get('kospi_change','—')}</div></div>
    <div class="metric-card"><div class="metric-label">코스닥 전일 종가</div><div class="metric-value up">{market.get('kosdaq_close','—')}</div><div class="metric-sub up">{market.get('kosdaq_change','—')}</div></div>
    <div class="metric-card"><div class="metric-label">오늘 시장 센티먼트</div><div class="metric-value warn-c">{prob.get('sentiment','—')}</div><div class="metric-sub warn-c">{prob.get('sentiment_reason','')}</div></div>
    <div class="metric-card"><div class="metric-label">원/달러 환율 (예상)</div><div class="metric-value up">{market.get('usd_krw','—')}</div><div class="metric-sub up">오늘 예상 환율</div></div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">📊 코스피 상승/하락 확률 <span class="badge badge-warn">{prob.get('kospi_badge','분석중')}</span></div>
      <div class="gauge-wrap">
        <div class="gauge-bar-outer">
          <div class="gauge-up-fill" style="width:{k_up}%;background:linear-gradient(90deg,#fca5a5,#dc2626);"><span class="gauge-bar-label">{k_up}%</span></div>
          <div class="gauge-down-fill" style="background:linear-gradient(90deg,#93c5fd,#2563eb);"><span class="gauge-bar-label">{100-k_up}%</span></div>
          <div class="gauge-center-line"></div>
        </div>
        <div class="gauge-labels">
          <span class="gauge-label-up">▲ 상승 {k_up}%</span>
          <span class="gauge-label-center">50%</span>
          <span class="gauge-label-down">하락 {100-k_up}% ▼</span>
        </div>
      </div>
      <div class="prob-divider">— 시나리오별 확률 —</div>
      {gauge_prob_rows(k_up, k_n)}
    </div>
    <div class="card">
      <div class="card-title">📊 코스닥 상승/하락 확률 <span class="badge badge-green">{prob.get('kosdaq_badge','분석중')}</span></div>
      <div class="gauge-wrap">
        <div class="gauge-bar-outer">
          <div class="gauge-up-fill" style="width:{kd_up}%;background:linear-gradient(90deg,#fca5a5,#dc2626);"><span class="gauge-bar-label">{kd_up}%</span></div>
          <div class="gauge-down-fill" style="background:linear-gradient(90deg,#93c5fd,#2563eb);"><span class="gauge-bar-label">{100-kd_up}%</span></div>
          <div class="gauge-center-line"></div>
        </div>
        <div class="gauge-labels">
          <span class="gauge-label-up">▲ 상승 {kd_up}%</span>
          <span class="gauge-label-center">50%</span>
          <span class="gauge-label-down">하락 {100-kd_up}% ▼</span>
        </div>
      </div>
      <div class="prob-divider">— 시나리오별 확률 —</div>
      {gauge_prob_rows(kd_up, kd_n)}
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">📈 코스피 장중 예상 <span class="badge badge-warn">{prob.get('kospi_badge','')}</span></div>
      <div class="pred-band">{pred_band_html(k_pred)}</div>
      <div class="chart-wrap"><canvas id="kospiChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">📈 코스닥 장중 예상 <span class="badge badge-green">{prob.get('kosdaq_badge','')}</span></div>
      <div class="pred-band">{pred_band_html(kd_pred)}</div>
      <div class="chart-wrap"><canvas id="kosdaqChart"></canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">🌍 전 거래일 미국 증시 &amp; 주요 지표 ({market.get('prev_date_label','—')})</div>
      <div class="futures-grid">{futures_html(news.get('us_futures',[]))}</div>
    </div>
    <div class="card">
      <div class="card-title">📅 이번 주 주요 경제 일정</div>
      {schedule_html(news.get('schedule',[]))}
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">🏦 오늘 업종 예상</div>
      {sectors_html(analysis.get('sectors',[]))}
    </div>
    <div class="card">
      <div class="card-title">🧠 AI 종합 분석</div>
      <div class="analysis-text">{analysis.get('analysis','분석 데이터를 불러오는 중 오류가 발생했습니다.')}</div>
      <div class="tags">{tags_html(analysis.get('tags',[]))}</div>
      <div class="notice">⚠️ 본 분석은 공개된 시장 데이터 및 뉴스를 바탕으로 한 참고용 예상이며, 실제 투자 판단의 근거로 사용하지 마세요.</div>
    </div>
  </div>

  <div class="footer">MIRAE ASSET Market Intelligence · 한국 주식시장 AI 대시보드 · {TODAY_FULL} · 참고용</div>
</div>

<script>
const labels = ['9:00','9:30','10:00','10:30','11:00','11:30','12:00','13:00','13:30','14:00','14:30','15:00','15:30'];
const kospiBase  = {json.dumps(k_base)};
const kospiHigh  = {json.dumps(k_high)};
const kospiLow   = {json.dumps(k_low)};
const kosdaqBase = {json.dumps(kd_base)};
const kosdaqHigh = {json.dumps(kd_high)};
const kosdaqLow  = {json.dumps(kd_low)};
function makeChart(id, base, high, low, color) {{
  new Chart(document.getElementById(id).getContext('2d'), {{
    type:'line',
    data:{{ labels, datasets:[
      {{label:'상단',data:high,borderColor:color,borderWidth:1,borderDash:[4,3],fill:false,tension:0.4,pointRadius:0}},
      {{label:'기본',data:base,borderColor:color,borderWidth:2.5,fill:false,tension:0.4,pointRadius:3,pointBackgroundColor:color}},
      {{label:'하단',data:low,borderColor:color,borderWidth:1,borderDash:[4,3],fill:'-1',backgroundColor:color+'14',tension:0.4,pointRadius:0}}
    ]}},
    options:{{
      responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{display:false}},tooltip:{{mode:'index',intersect:false}}}},
      scales:{{
        x:{{grid:{{display:false}},ticks:{{font:{{size:10}},maxRotation:0,maxTicksLimit:7}}}},
        y:{{grid:{{color:'rgba(0,0,0,0.04)'}},ticks:{{font:{{size:10}},callback:v=>v.toLocaleString()}}}}
      }}
    }}
  }});
}}
makeChart('kospiChart',  kospiBase,  kospiHigh,  kospiLow,  '#dc2626');
makeChart('kosdaqChart', kosdaqBase, kosdaqHigh, kosdaqLow, '#2563eb');
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"✅ index.html 생성 완료! ({len(HTML):,} bytes)")
