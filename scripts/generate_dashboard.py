#!/usr/bin/env python3
import anthropic, json, re, time
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
DAYS_KO = ['월','화','수','목','금','토','일']
TODAY_FULL = now.strftime("%Y년 %-m월 %-d일") + " (" + DAYS_KO[now.weekday()] + ")"
TODAY_YMD  = now.strftime("%Y-%m-%d")
GENERATED_AT = now.strftime("%Y년 %-m월 %-d일 %H:%M KST")

# 전 거래일 계산 (오늘이 월요일이면 금요일, 아니면 전날 평일)
def get_prev_trading_day(d):
    wd = d.weekday()
    if wd == 0:   delta = 3  # 월→금
    elif wd == 6: delta = 2  # 일→금
    elif wd == 5: delta = 1  # 토→금
    else:         delta = 1
    prev = d - timedelta(days=delta)
    return prev

prev_day = get_prev_trading_day(now)
PREV_FULL  = prev_day.strftime("%Y년 %-m월 %-d일") + " (" + DAYS_KO[prev_day.weekday()] + ")"
PREV_SHORT = prev_day.strftime("%-m/%-d") + " (" + DAYS_KO[prev_day.weekday()] + ")"

client = anthropic.Anthropic()

def call_claude(prompt):
    response = client.messages.create(
        model="claude-haiku-4-5",
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

# ── 1차 호출: 전일 확정 종가 데이터 수집 ──
print("📡 [1/2] 전일(" + PREV_SHORT + ") 확정 종가 데이터 수집 중...")
prompt1 = (
    "오늘은 " + TODAY_YMD + "이고, 지금 시각은 오전 8시(KST)입니다.\n"
    "전 거래일(" + PREV_FULL + ") 확정 종가 데이터를 웹검색으로 수집해 아래 JSON 형식으로만 반환하세요.\n"
    "반드시 전일 최종 확정된 종가를 사용하고, 장중 추정치나 예상치는 사용하지 마세요.\n"
    "마크다운 없이 JSON만 출력하세요:\n"
    "{\n"
    '  "kospi": {"close": "확정종가(예:2,650.34)", "chg_pt": "등락포인트(예:+32.12p)", "chg_pct": "등락률(예:+0.41%)"},\n'
    '  "kosdaq": {"close": "확정종가", "chg_pt": "등락포인트", "chg_pct": "등락률"},\n'
    '  "usd_krw": "원달러환율(예:1,380원)",\n'
    '  "sp500": {"close": "확정종가", "chg_pt": "등락포인트", "chg_pct": "등락률"},\n'
    '  "nasdaq": {"close": "확정종가", "chg_pt": "등락포인트", "chg_pct": "등락률"},\n'
    '  "dow": {"close": "확정종가", "chg_pt": "등락포인트", "chg_pct": "등락률"},\n'
    '  "wti": "WTI유가(예:$72.5)",\n'
    '  "us10y": "미10년물금리(예:4.35%)",\n'
    '  "weekly_kospi_chg": "코스피 주간 등락률(예:+2.3%)",\n'
    '  "banner_title": "전거래일 핵심 요약 한줄(예:코스피 0.41% 상승 · S&P500 8주 연속 랠리)",\n'
    '  "news": [\n'
    '    {"type": "bull", "tag": "🇺🇸 미국 증시 (' + PREV_SHORT + ')", "title": "헤드라인", "desc": "2-3문장 요약"},\n'
    '    {"type": "warn", "tag": "📅 이번주 핵심 이벤트", "title": "헤드라인", "desc": "2-3문장 요약"},\n'
    '    {"type": "neutral", "tag": "⚠️ 주요 리스크", "title": "헤드라인", "desc": "2-3문장 요약"}\n'
    '  ],\n'
    '  "schedule": [\n'
    '    {"date": "날짜(예:5/28)", "day": "요일(예:수)", "today": false, "title": "이벤트명", "desc": "설명", "imp": "high"},\n'
    '    {"date": "5/29", "day": "목", "today": false, "title": "이벤트명", "desc": "설명", "imp": "med"}\n'
    '  ],\n'
    '  "us_market": [\n'
    '    {"name": "S&P 500", "val": "종가", "chg": "등락률 및 코멘트", "cls": "up"},\n'
    '    {"name": "나스닥", "val": "종가", "chg": "등락률", "cls": "up"},\n'
    '    {"name": "다우존스", "val": "종가", "chg": "등락률 및 특이사항", "cls": "up"},\n'
    '    {"name": "필라델피아 반도체", "val": "수치또는강약", "chg": "코멘트", "cls": "up"},\n'
    '    {"name": "WTI 유가", "val": "가격", "chg": "등락 및 원인", "cls": "down"},\n'
    '    {"name": "미 10년물 금리", "val": "금리", "chg": "코멘트", "cls": "neutral"},\n'
    '    {"name": "원/달러 환율", "val": "환율", "chg": "코멘트", "cls": "up"},\n'
    '    {"name": "코스피200 야간선물", "val": "수치", "chg": "코멘트", "cls": "neutral"}\n'
    '  ]\n'
    '}'
)

raw1 = call_claude(prompt1)
d1 = safe_json(raw1)
print("  코스피: " + d1.get('kospi',{}).get('close','—') + ", S&P500: " + d1.get('sp500',{}).get('close','—'))

time.sleep(65)

# ── 2차 호출: 오늘 장세 전망 분석 ──
print("🧠 [2/2] 오늘 장세 전망 분석 중...")
kospi_data  = str(d1.get('kospi',  {}).get('close',''))
sp500_data  = str(d1.get('sp500',  {}).get('close',''))
nasdaq_data = str(d1.get('nasdaq', {}).get('close',''))

prompt2 = (
    "오늘은 " + TODAY_YMD + " 오전 8시(KST)입니다.\n"
    "전 거래일(" + PREV_FULL + ") 확정 데이터: 코스피=" + kospi_data + ", S&P500=" + sp500_data + ", 나스닥=" + nasdaq_data + "\n"
    "이 확정 데이터를 바탕으로 오늘 한국 증시 전망을 분석해 아래 JSON 형식으로만 반환하세요.\n"
    "마크다운 없이 JSON만 출력하세요:\n"
    "{\n"
    '  "sentiment": "오늘 장세 전망 한마디(예:중립~소폭 강세)",\n'
    '  "sentiment_reason": "전망 근거 한줄",\n'
    '  "kospi_up": 55,\n'
    '  "kospi_neutral": 15,\n'
    '  "kosdaq_up": 58,\n'
    '  "kosdaq_neutral": 14,\n'
    '  "kospi_badge": "코스피 핵심 키워드(예:외국인 수급 주의)",\n'
    '  "kosdaq_badge": "코스닥 핵심 키워드(예:기관 매수 기대)",\n'
    '  "kospi_range": {"bear": "하단범위(예:2,580~2,620)", "bear_prob": 30, "base": "기본범위(예:2,630~2,670)", "base_prob": 50, "bull": "상단범위(예:2,670~2,710)", "bull_prob": 20},\n'
    '  "kosdaq_range": {"bear": "하단범위", "bear_prob": 25, "base": "기본범위", "base_prob": 55, "bull": "상단범위", "bull_prob": 20},\n'
    '  "kospi_base": 2650,\n'
    '  "kosdaq_base": 850,\n'
    '  "sectors": [\n'
    '    {"name": "반도체", "chg": 1.5, "note": "전망 이유"},\n'
    '    {"name": "2차전지", "chg": 0.8, "note": "전망 이유"},\n'
    '    {"name": "바이오·제약", "chg": 0.5, "note": "전망 이유"},\n'
    '    {"name": "항공·여행", "chg": 0.3, "note": "전망 이유"},\n'
    '    {"name": "금융", "chg": -0.2, "note": "전망 이유"},\n'
    '    {"name": "건설·부동산", "chg": -0.5, "note": "전망 이유"},\n'
    '    {"name": "유틸리티", "chg": -0.8, "note": "전망 이유"}\n'
    '  ],\n'
    '  "analysis": "전일 확정 데이터 기반 오늘 장세 종합 분석 2-3문단 (HTML strong 태그 사용 가능, 데이터 기준일 명시 포함)",\n'
    '  "tags": [\n'
    '    {"type": "bull", "text": "긍정요인"},\n'
    '    {"type": "bull", "text": "긍정요인2"},\n'
    '    {"type": "warn", "text": "주의요인"},\n'
    '    {"type": "bear", "text": "리스크요인"},\n'
    '    {"type": "neutral", "text": "중립요인"},\n'
    '    {"type": "purple", "text": "주요이벤트"}\n'
    '  ]\n'
    '}'
)

raw2 = call_claude(prompt2)
d2 = safe_json(raw2)
print("  센티먼트: " + d2.get('sentiment','—'))

# ── HTML 헬퍼 함수 ──
def prob_rows(up, neu):
    dn = 100 - up - neu
    return (
        '<div class="prob-row"><span class="prob-name up">추가 상승</span>'
        '<div class="prob-bar-bg"><div class="prob-bar-inner" style="width:' + str(up) + '%;background:linear-gradient(90deg,#ef4444,#dc2626);">'
        '<span style="font-size:10px;font-weight:700;color:#fff;">' + str(up) + '%</span></div></div>'
        '<span class="prob-pct up">' + str(up) + '%</span></div>'
        '<div class="prob-row"><span class="prob-name neutral">횡보</span>'
        '<div class="prob-bar-bg"><div class="prob-bar-inner" style="width:' + str(neu) + '%;background:#9ca3af;">'
        '<span style="font-size:10px;font-weight:700;color:#fff;">' + str(neu) + '%</span></div></div>'
        '<span class="prob-pct neutral">' + str(neu) + '%</span></div>'
        '<div class="prob-row"><span class="prob-name down">하락</span>'
        '<div class="prob-bar-bg"><div class="prob-bar-inner" style="width:' + str(dn) + '%;background:linear-gradient(90deg,#3b82f6,#2563eb);">'
        '<span style="font-size:10px;font-weight:700;color:#fff;">' + str(dn) + '%</span></div></div>'
        '<span class="prob-pct down">' + str(dn) + '%</span></div>'
    )

def news_html(lst):
    r = ""
    for n in (lst or [])[:3]:
        t = n.get("type","neutral")
        cls = "bull" if t=="bull" else ("warn" if t=="warn" else "")
        r += ('<div class="news-item ' + cls + '">'
              '<div class="news-tag">' + n.get("tag","") + '</div>'
              '<div class="news-title">' + n.get("title","") + '</div>'
              '<div class="news-desc">' + n.get("desc","") + '</div></div>')
    return r

def sched_html(lst):
    r = ""
    for s in (lst or [])[:5]:
        ic = "sch-high" if s.get("imp")=="high" else "sch-med"
        it = "주요" if s.get("imp")=="high" else "중요"
        td = "<br>오늘" if s.get("today") else ""
        r += ('<div class="schedule-row">'
              '<span class="sch-date">' + s.get("date","") + '/' + s.get("day","") + td + '</span>'
              '<div class="sch-content">'
              '<div class="sch-title">' + s.get("title","") + ' <span class="sch-badge ' + ic + '">' + it + '</span></div>'
              '<div class="sch-desc">' + s.get("desc","") + '</div></div></div>')
    return r

def us_market_html(lst):
    r = ""
    for f in (lst or []):
        r += ('<div class="futures-item">'
              '<div class="futures-name">' + f.get("name","") + '</div>'
              '<div class="futures-val ' + f.get("cls","") + '">' + f.get("val","—") + '</div>'
              '<div class="futures-chg ' + f.get("cls","") + '">' + f.get("chg","") + '</div></div>')
    return r

def sectors_html(lst):
    if not lst: return ""
    mx = max(abs(s.get("chg",0)) for s in lst) or 1
    r = ""
    for s in lst:
        c = s.get("chg",0); pct = abs(c)/mx*100
        col = "#dc2626" if c>=0 else "#2563eb"
        cls = "up" if c>=0 else "down"
        sg = "+" if c>=0 else ""
        r += ('<div class="sector-row">'
              '<span class="sector-name">' + s.get("name","") + '</span>'
              '<div class="sector-bar-bg"><div class="sector-bar" style="width:' + str(round(pct)) + '%;background:' + col + ';"></div></div>'
              '<span class="sector-pct ' + cls + '">' + sg + str(c) + '%</span></div>')
    return r

def tags_html(lst):
    return "".join(
        '<span class="tag tag-' + t.get("type","neutral") + '">' + t.get("text","") + '</span>'
        for t in (lst or [])
    )

def pred_band_html(p):
    return (
        '<div class="pred-item pred-bear"><div class="pred-label">약세</div>'
        '<div class="pred-range down">' + p.get("bear","—") + '</div>'
        '<div class="pred-prob">' + str(p.get("bear_prob", p.get("bp","—"))) + '%</div></div>'
        '<div class="pred-item pred-base"><div class="pred-label">기본</div>'
        '<div class="pred-range">' + p.get("base","—") + '</div>'
        '<div class="pred-prob">' + str(p.get("base_prob", p.get("bap","—"))) + '%</div></div>'
        '<div class="pred-item pred-bull"><div class="pred-label">강세</div>'
        '<div class="pred-range up">' + p.get("bull","—") + '</div>'
        '<div class="pred-prob">' + str(p.get("bull_prob", p.get("bup","—"))) + '%</div></div>'
    )

def gen_lines(base, rng):
    bh_str = rng.get("bull",""); bl_str = rng.get("bear","")
    nb = re.findall(r'[\d]+\.?\d*', bh_str.replace(',',''))
    nd = re.findall(r'[\d]+\.?\d*', bl_str.replace(',',''))
    bh = float(nb[-1]) if nb else base*1.012
    bl = float(nd[0])  if nd else base*0.988
    n = 13
    hi = [round(base+(bh-base)*(i/(n-1)), 2) for i in range(n)]
    lo = [round(base+(bl-base)*(i/(n-1)), 2) for i in range(n)]
    ba = [(h+l)/2 for h,l in zip(hi,lo)]
    return ba, hi, lo

# 데이터 변수 정리
kospi  = d1.get('kospi',  {})
kosdaq = d1.get('kosdaq', {})
sp500  = d1.get('sp500',  {})
nasdaq = d1.get('nasdaq', {})
dow    = d1.get('dow',    {})

k_up  = d2.get('kospi_up',      55)
k_n   = d2.get('kospi_neutral', 15)
kd_up = d2.get('kosdaq_up',     58)
kd_n  = d2.get('kosdaq_neutral',14)

kp  = d2.get('kospi_range',  {})
kdp = d2.get('kosdaq_range', {})

kb,  kh,  kl  = gen_lines(d2.get('kospi_base',  2650), kp)
kdb, kdh, kdl = gen_lines(d2.get('kosdaq_base',  850), kdp)

# 코스피 등락 표시
kospi_chg_display = kospi.get('chg_pt','') + ' (' + kospi.get('chg_pct','') + ')'
kosdaq_chg_display = kosdaq.get('chg_pt','') + ' (' + kosdaq.get('chg_pct','') + ')'

CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif; background: #f0f3f8; color: #1a1a2e; font-size: 14px; }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
  .mw-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; flex-wrap: wrap; gap: 8px; }
  .mw-logo-box { background: #E8380D; border-radius: 4px; padding: 5px 12px; }
  .mw-logo-text { font-size: 13px; font-weight: 500; color: #fff; letter-spacing: 0.02em; }
  .mw-logo-sub { font-size: 11px; color: #666; margin-left: 8px; }
  .mw-date-area { display: flex; align-items: center; gap: 8px; }
  .mw-date { font-size: 12px; color: #666; }
  .mw-live { display: flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; color: #E8380D; background: #fdf0ed; border: 0.5px solid #f5b8a8; border-radius: 99px; padding: 2px 10px; }
  .mw-main { border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.1); margin-bottom: 16px; }
  .mw-header-bar { background: #043B72; padding: 18px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
  .mw-title-en { font-size: 10px; font-weight: 500; letter-spacing: 0.14em; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 5px; }
  .mw-title-ko { font-size: 22px; font-weight: 500; color: #fff; letter-spacing: -0.02em; }
  .mw-title-ko em { color: #F58220; font-style: normal; }
  .mw-title-desc { font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 4px; }
  .mw-header-right { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
  .mw-sentiment-chip { display: flex; align-items: center; gap: 7px; background: rgba(255,255,255,0.1); border: 0.5px solid rgba(255,255,255,0.2); border-radius: 99px; padding: 5px 14px; }
  .mw-s-dot { width: 7px; height: 7px; border-radius: 50%; background: #4ade80; }
  .mw-s-label { font-size: 11px; color: rgba(255,255,255,0.65); }
  .mw-s-val { font-size: 12px; font-weight: 600; color: #fff; }
  .mw-kpi-row { display: flex; align-items: center; gap: 12px; }
  .mw-kpi { text-align: right; }
  .mw-kpi-val { font-size: 16px; font-weight: 600; color: #fca5a5; }
  .mw-kpi-label { font-size: 10px; color: rgba(255,255,255,0.5); margin-top: 1px; }
  .mw-kpi-div { width: 0.5px; height: 32px; background: rgba(255,255,255,0.2); }
  .mw-bottom-bar { background: #f8f9fc; padding: 9px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; border-top: 1px solid #e5e7eb; }
  .mw-sources { display: flex; align-items: center; gap: 6px; }
  .mw-src-label { font-size: 11px; color: #888; }
  .mw-pill { font-size: 10px; padding: 2px 8px; border-radius: 99px; border: 0.5px solid #d1d5db; color: #666; background: #fff; }
  .mw-update { font-size: 11px; color: #888; }
  .mw-orange-line { height: 3px; background: #F58220; }
  .data-basis-bar { background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 8px 16px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; font-size: 11px; color: #92400e; }
  .data-basis-bar strong { font-weight: 700; }
  .result-banner { background: linear-gradient(135deg, #043B72 0%, #1d5fa8 100%); border-radius: 12px; padding: 14px 20px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(4,59,114,0.2); }
  .result-banner h3 { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.7); margin-bottom: 10px; }
  .result-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .result-item { text-align: center; }
  .result-label { font-size: 10px; color: rgba(255,255,255,0.6); margin-bottom: 3px; }
  .result-val { font-size: 17px; font-weight: 700; color: #fca5a5; }
  .result-chg { font-size: 11px; color: rgba(255,255,255,0.75); margin-top: 2px; }
  .news-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
  .news-item { background: #fff; border-radius: 10px; padding: 12px 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); border-left: 3px solid #2563eb; }
  .news-item.bull { border-left-color: #dc2626; }
  .news-item.warn { border-left-color: #d97706; }
  .news-tag { font-size: 10px; font-weight: 700; color: #2563eb; margin-bottom: 4px; }
  .news-item.bull .news-tag { color: #dc2626; }
  .news-item.warn .news-tag { color: #d97706; }
  .news-title { font-size: 12px; font-weight: 600; margin-bottom: 3px; line-height: 1.5; }
  .news-desc { font-size: 11px; color: #666; line-height: 1.5; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
  .metric-card { background: #fff; border-radius: 10px; padding: 14px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
  .metric-label { font-size: 11px; color: #888; margin-bottom: 4px; }
  .metric-value { font-size: 22px; font-weight: 700; }
  .metric-sub { font-size: 12px; margin-top: 3px; }
  .card { background: #fff; border-radius: 12px; padding: 16px 18px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
  .card-title { font-size: 13px; font-weight: 600; color: #444; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .up { color: #dc2626; } .down { color: #2563eb; } .neutral { color: #888; } .warnc { color: #d97706; }
  .badge { font-size: 10px; padding: 2px 8px; border-radius: 99px; font-weight: 600; }
  .badge-up { background: #fee2e2; color: #b91c1c; }
  .badge-warn { background: #fef3c7; color: #92400e; }
  .badge-blue { background: #dbeafe; color: #1d4ed8; }
  .badge-green { background: #d1fae5; color: #065f46; }
  .badge-msci { background: #ede9fe; color: #5b21b6; }
  .gauge-wrap { margin-bottom: 10px; }
  .gauge-bar-outer { width: 100%; height: 28px; border-radius: 14px; overflow: hidden; display: flex; position: relative; background: #e5e7eb; margin-bottom: 5px; }
  .gauge-up-fill { height: 100%; display: flex; align-items: center; justify-content: center; }
  .gauge-down-fill { height: 100%; flex: 1; display: flex; align-items: center; justify-content: center; }
  .gauge-bar-label { font-size: 11px; font-weight: 700; color: #fff; }
  .gauge-center-line { position: absolute; left: 50%; top: 0; bottom: 0; width: 2px; background: rgba(255,255,255,0.5); }
  .gauge-labels { display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; }
  .gauge-label-up { color: #dc2626; } .gauge-label-center { color: #999; } .gauge-label-down { color: #2563eb; }
  .prob-divider { text-align: center; font-size: 10px; color: #999; margin: 6px 0; }
  .prob-row { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
  .prob-row:last-child { margin-bottom: 0; }
  .prob-name { font-size: 11px; font-weight: 600; width: 56px; flex-shrink: 0; }
  .prob-bar-bg { flex: 1; height: 18px; border-radius: 9px; overflow: hidden; background: #e5e7eb; }
  .prob-bar-inner { height: 100%; border-radius: 9px; display: flex; align-items: center; justify-content: flex-end; padding-right: 7px; }
  .prob-pct { font-size: 13px; font-weight: 700; width: 34px; text-align: right; flex-shrink: 0; }
  .pred-band { display: flex; gap: 6px; margin-bottom: 10px; }
  .pred-item { flex: 1; padding: 7px 8px; border-radius: 8px; text-align: center; }
  .pred-bear { background: #eff6ff; } .pred-base { background: #f9fafb; } .pred-bull { background: #fef2f2; }
  .pred-label { font-size: 10px; color: #888; margin-bottom: 3px; }
  .pred-range { font-size: 12px; font-weight: 700; }
  .pred-prob { font-size: 10px; color: #888; margin-top: 2px; }
  .futures-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
  .futures-item { padding: 8px 10px; background: #f9fafb; border-radius: 8px; }
  .futures-name { font-size: 10px; color: #888; margin-bottom: 2px; }
  .futures-val { font-size: 14px; font-weight: 700; }
  .futures-chg { font-size: 11px; }
  .sector-row { display: flex; align-items: center; gap: 8px; padding: 5px 0; border-bottom: 1px solid #f0f0f0; }
  .sector-row:last-child { border-bottom: none; }
  .sector-name { width: 82px; font-size: 11px; flex-shrink: 0; font-weight: 500; }
  .sector-bar-bg { flex: 1; height: 5px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }
  .sector-bar { height: 100%; border-radius: 3px; }
  .sector-pct { width: 44px; text-align: right; font-size: 11px; font-weight: 700; flex-shrink: 0; }
  .schedule-row { display: flex; align-items: flex-start; gap: 10px; padding: 7px 0; border-bottom: 1px solid #f0f0f0; }
  .schedule-row:last-child { border-bottom: none; }
  .sch-date { font-size: 11px; font-weight: 700; width: 36px; flex-shrink: 0; color: #043B72; }
  .sch-content { flex: 1; }
  .sch-title { font-size: 12px; font-weight: 600; }
  .sch-desc { font-size: 11px; color: #666; margin-top: 2px; }
  .sch-badge { font-size: 10px; padding: 1px 7px; border-radius: 99px; font-weight: 600; margin-left: 5px; }
  .sch-high { background: #fee2e2; color: #b91c1c; }
  .sch-med { background: #fef3c7; color: #92400e; }
  .analysis-text { font-size: 13px; line-height: 1.8; color: #333; }
  .tags { margin-top: 10px; }
  .tag { display: inline-block; font-size: 11px; padding: 2px 9px; border-radius: 99px; margin: 2px 3px 2px 0; }
  .tag-bull { background: #fee2e2; color: #b91c1c; }
  .tag-bear { background: #dbeafe; color: #1d4ed8; }
  .tag-neutral { background: #f3f4f6; color: #555; }
  .tag-warn { background: #fef3c7; color: #92400e; }
  .tag-purple { background: #ede9fe; color: #5b21b6; }
  .notice { font-size: 11px; color: #999; background: #f9fafb; border-radius: 8px; padding: 9px 12px; margin-top: 12px; border: 1px solid #e5e7eb; }
  .chart-wrap { position: relative; height: 165px; }
  .footer { text-align: center; margin-top: 20px; font-size: 11px; color: #bbb; padding-bottom: 16px; }
  @media(max-width:768px) {
    .grid-4 { grid-template-columns: repeat(2,1fr); }
    .grid-2 { grid-template-columns: 1fr; }
    .news-row { grid-template-columns: 1fr; }
    .result-grid { grid-template-columns: repeat(2,1fr); }
  }
"""

HTML = (
"<!DOCTYPE html>\n"
"<html lang='ko'>\n"
"<head>\n"
"<meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
"<title>한국 주식시장 AI 대시보드 | " + TODAY_FULL + "</title>\n"
"<script src='https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'></script>\n"
"<style>" + CSS + "</style>\n"
"</head>\n"
"<body>\n"
"<div class='container'>\n"

# 타이틀
"  <div class='mw-top'>\n"
"    <div style='display:flex;align-items:center;gap:8px;'>\n"
"      <div class='mw-logo-box'><span class='mw-logo-text'>MIRAE ASSET</span></div>\n"
"      <span class='mw-logo-sub'>Market Intelligence</span>\n"
"    </div>\n"
"    <div class='mw-date-area'>\n"
"      <span class='mw-date'>" + TODAY_FULL + "</span>\n"
"      <span class='mw-live'>● AI 생성</span>\n"
"    </div>\n"
"  </div>\n"

"  <div class='mw-main'>\n"
"    <div class='mw-header-bar'>\n"
"      <div>\n"
"        <div class='mw-title-en'>Korea Equity Market AI Dashboard</div>\n"
"        <div class='mw-title-ko'>한국 주식시장 <em>AI</em> 대시보드</div>\n"
"        <div class='mw-title-desc'>전일 미국 증시 · 야간선물 · 환율 · 주요 경제 뉴스 종합 분석</div>\n"
"      </div>\n"
"      <div class='mw-header-right'>\n"
"        <div class='mw-sentiment-chip'>\n"
"          <div class='mw-s-dot'></div>\n"
"          <span class='mw-s-label'>오늘 장세 전망</span>\n"
"          <span class='mw-s-val'>" + d2.get('sentiment','—') + "</span>\n"
"        </div>\n"
"        <div class='mw-kpi-row'>\n"
"          <div class='mw-kpi'><div class='mw-kpi-val'>" + kospi.get('close','—') + "</div><div class='mw-kpi-label'>코스피 전일종가(" + PREV_SHORT + ")</div></div>\n"
"          <div class='mw-kpi-div'></div>\n"
"          <div class='mw-kpi'><div class='mw-kpi-val'>" + kospi.get('chg_pct','—') + "</div><div class='mw-kpi-label'>전일 등락률</div></div>\n"
"          <div class='mw-kpi-div'></div>\n"
"          <div class='mw-kpi'><div class='mw-kpi-val'>" + kosdaq.get('close','—') + "</div><div class='mw-kpi-label'>코스닥 전일종가</div></div>\n"
"        </div>\n"
"      </div>\n"
"    </div>\n"
"    <div class='mw-bottom-bar'>\n"
"      <div class='mw-sources'>\n"
"        <span class='mw-src-label'>데이터 소스</span>\n"
"        <span class='mw-pill'>KRX</span><span class='mw-pill'>Bloomberg</span><span class='mw-pill'>Reuters</span><span class='mw-pill'>뉴스 검색</span><span class='mw-pill'>야간선물</span>\n"
"      </div>\n"
"      <span class='mw-update'>AI 생성: " + GENERATED_AT + " | 데이터 기준: " + PREV_FULL + " 확정 종가</span>\n"
"    </div>\n"
"    <div class='mw-orange-line'></div>\n"
"  </div>\n"

# 데이터 기준일 명시 바
"  <div class='data-basis-bar'>\n"
"    📌 <strong>데이터 기준:</strong> " + PREV_FULL + " 확정 종가 기준 &nbsp;|&nbsp; 생성 시각: " + GENERATED_AT + " &nbsp;|&nbsp; 오늘(" + TODAY_FULL + ") 장세 전망 분석\n"
"  </div>\n"

# 전 거래일 결과 배너
"  <div class='result-banner'>\n"
"    <h3>📌 " + d1.get('banner_title','전 거래일 실제 마감 결과') + "</h3>\n"
"    <div class='result-grid'>\n"
"      <div class='result-item'><div class='result-label'>코스피 종가 (" + PREV_SHORT + ")</div><div class='result-val'>" + kospi.get('close','—') + "</div><div class='result-chg'>▲ " + kospi.get('chg_pt','—') + " (" + kospi.get('chg_pct','—') + ")</div></div>\n"
"      <div class='result-item'><div class='result-label'>S&amp;P 500 (" + PREV_SHORT + ")</div><div class='result-val'>" + sp500.get('close','—') + "</div><div class='result-chg'>" + sp500.get('chg_pt','—') + " (" + sp500.get('chg_pct','—') + ")</div></div>\n"
"      <div class='result-item'><div class='result-label'>나스닥</div><div class='result-val'>" + nasdaq.get('close','—') + "</div><div class='result-chg'>" + nasdaq.get('chg_pt','—') + " (" + nasdaq.get('chg_pct','—') + ")</div></div>\n"
"      <div class='result-item'><div class='result-label'>다우존스</div><div class='result-val'>" + dow.get('close','—') + "</div><div class='result-chg'>" + dow.get('chg_pt','—') + " (" + dow.get('chg_pct','—') + ")</div></div>\n"
"    </div>\n"
"  </div>\n"

# 뉴스
"  <div class='news-row'>" + news_html(d1.get('news',[])) + "</div>\n"

# 핵심 지표
"  <div class='grid-4'>\n"
"    <div class='metric-card'><div class='metric-label'>코스피 확정 종가 (" + PREV_SHORT + ")</div><div class='metric-value up'>" + kospi.get('close','—') + "</div><div class='metric-sub up'>" + kospi_chg_display + "</div></div>\n"
"    <div class='metric-card'><div class='metric-label'>코스닥 확정 종가 (" + PREV_SHORT + ")</div><div class='metric-value up'>" + kosdaq.get('close','—') + "</div><div class='metric-sub up'>" + kosdaq_chg_display + "</div></div>\n"
"    <div class='metric-card'><div class='metric-label'>오늘 장세 전망</div><div class='metric-value warnc'>" + d2.get('sentiment','—') + "</div><div class='metric-sub warnc'>" + d2.get('sentiment_reason','') + "</div></div>\n"
"    <div class='metric-card'><div class='metric-label'>원/달러 환율 (" + PREV_SHORT + ")</div><div class='metric-value up'>" + d1.get('usd_krw','—') + "</div><div class='metric-sub up'>전일 확정 환율</div></div>\n"
"  </div>\n"

# 확률 게이지
"  <div class='grid-2'>\n"
"    <div class='card'>\n"
"      <div class='card-title'>📊 코스피 오늘 방향성 전망 <span class='badge badge-warn'>" + d2.get('kospi_badge','') + "</span></div>\n"
"      <div class='gauge-wrap'>\n"
"        <div class='gauge-bar-outer'>\n"
"          <div class='gauge-up-fill' style='width:" + str(k_up) + "%;background:linear-gradient(90deg,#fca5a5,#dc2626);'><span class='gauge-bar-label'>" + str(k_up) + "%</span></div>\n"
"          <div class='gauge-down-fill' style='background:linear-gradient(90deg,#93c5fd,#2563eb);'><span class='gauge-bar-label'>" + str(100-k_up) + "%</span></div>\n"
"          <div class='gauge-center-line'></div>\n"
"        </div>\n"
"        <div class='gauge-labels'><span class='gauge-label-up'>▲ 상승 " + str(k_up) + "%</span><span class='gauge-label-center'>50%</span><span class='gauge-label-down'>하락 " + str(100-k_up) + "% ▼</span></div>\n"
"      </div>\n"
"      <div class='prob-divider'>— 시나리오별 확률 —</div>\n"
"      " + prob_rows(k_up, k_n) + "\n"
"    </div>\n"
"    <div class='card'>\n"
"      <div class='card-title'>📊 코스닥 오늘 방향성 전망 <span class='badge badge-green'>" + d2.get('kosdaq_badge','') + "</span></div>\n"
"      <div class='gauge-wrap'>\n"
"        <div class='gauge-bar-outer'>\n"
"          <div class='gauge-up-fill' style='width:" + str(kd_up) + "%;background:linear-gradient(90deg,#fca5a5,#dc2626);'><span class='gauge-bar-label'>" + str(kd_up) + "%</span></div>\n"
"          <div class='gauge-down-fill' style='background:linear-gradient(90deg,#93c5fd,#2563eb);'><span class='gauge-bar-label'>" + str(100-kd_up) + "%</span></div>\n"
"          <div class='gauge-center-line'></div>\n"
"        </div>\n"
"        <div class='gauge-labels'><span class='gauge-label-up'>▲ 상승 " + str(kd_up) + "%</span><span class='gauge-label-center'>50%</span><span class='gauge-label-down'>하락 " + str(100-kd_up) + "% ▼</span></div>\n"
"      </div>\n"
"      <div class='prob-divider'>— 시나리오별 확률 —</div>\n"
"      " + prob_rows(kd_up, kd_n) + "\n"
"    </div>\n"
"  </div>\n"

# 장중 예상 범위 차트
"  <div class='grid-2'>\n"
"    <div class='card'>\n"
"      <div class='card-title'>📈 코스피 오늘 예상 범위 <span class='badge badge-warn'>" + d2.get('kospi_badge','') + "</span></div>\n"
"      <div class='pred-band'>" + pred_band_html(kp) + "</div>\n"
"      <div class='chart-wrap'><canvas id='kospiChart'></canvas></div>\n"
"    </div>\n"
"    <div class='card'>\n"
"      <div class='card-title'>📈 코스닥 오늘 예상 범위 <span class='badge badge-green'>" + d2.get('kosdaq_badge','') + "</span></div>\n"
"      <div class='pred-band'>" + pred_band_html(kdp) + "</div>\n"
"      <div class='chart-wrap'><canvas id='kosdaqChart'></canvas></div>\n"
"    </div>\n"
"  </div>\n"

# 미국 증시 + 일정
"  <div class='grid-2'>\n"
"    <div class='card'>\n"
"      <div class='card-title'>🌍 전 거래일 미국 증시 &amp; 주요 지표 (" + PREV_SHORT + ")</div>\n"
"      <div class='futures-grid'>" + us_market_html(d1.get('us_market',[])) + "</div>\n"
"    </div>\n"
"    <div class='card'>\n"
"      <div class='card-title'>📅 이번 주 주요 경제 일정</div>\n"
"      " + sched_html(d1.get('schedule',[])) + "\n"
"    </div>\n"
"  </div>\n"

# 업종 + AI 분석
"  <div class='grid-2'>\n"
"    <div class='card'>\n"
"      <div class='card-title'>🏦 오늘 업종별 전망</div>\n"
"      " + sectors_html(d2.get('sectors',[])) + "\n"
"    </div>\n"
"    <div class='card'>\n"
"      <div class='card-title'>🧠 AI 종합 분석 <span style='font-size:10px;color:#999;font-weight:400;'>| 기준: " + PREV_FULL + " 확정 종가</span></div>\n"
"      <div class='analysis-text'>" + d2.get('analysis','분석 데이터를 불러오는 중 오류가 발생했습니다.') + "</div>\n"
"      <div class='tags'>" + tags_html(d2.get('tags',[])) + "</div>\n"
"      <div class='notice'>⚠️ 본 분석은 " + PREV_FULL + " 확정 종가 기준으로 생성된 참고용 전망입니다. 실제 투자 판단의 근거로 사용하지 마세요.</div>\n"
"    </div>\n"
"  </div>\n"

"  <div class='footer'>MIRAE ASSET Market Intelligence · 한국 주식시장 AI 대시보드 · " + TODAY_FULL + " · 데이터 기준: " + PREV_FULL + " · 참고용</div>\n"
"</div>\n"

"<script>\n"
"const L=['9:00','9:30','10:00','10:30','11:00','11:30','12:00','13:00','13:30','14:00','14:30','15:00','15:30'];\n"
"function makeChart(id,base,high,low,color){\n"
"  new Chart(document.getElementById(id).getContext('2d'),{\n"
"    type:'line',\n"
"    data:{labels:L,datasets:[\n"
"      {label:'상단',data:high,borderColor:color,borderWidth:1,borderDash:[4,3],fill:false,tension:.4,pointRadius:0},\n"
"      {label:'기본',data:base,borderColor:color,borderWidth:2.5,fill:false,tension:.4,pointRadius:3,pointBackgroundColor:color},\n"
"      {label:'하단',data:low,borderColor:color,borderWidth:1,borderDash:[4,3],fill:'-1',backgroundColor:color+'14',tension:.4,pointRadius:0}\n"
"    ]},\n"
"    options:{responsive:true,maintainAspectRatio:false,\n"
"      plugins:{legend:{display:false},tooltip:{mode:'index',intersect:false}},\n"
"      scales:{x:{grid:{display:false},ticks:{font:{size:10},maxRotation:0,maxTicksLimit:7}},\n"
"               y:{grid:{color:'rgba(0,0,0,.04)'},ticks:{font:{size:10},callback:v=>v.toLocaleString()}}}\n"
"    }\n"
"  });\n"
"}\n"
"makeChart('kospiChart'," + json.dumps(kb) + "," + json.dumps(kh) + "," + json.dumps(kl) + ",'#dc2626');\n"
"makeChart('kosdaqChart'," + json.dumps(kdb) + "," + json.dumps(kdh) + "," + json.dumps(kdl) + ",'#2563eb');\n"
"</script>\n"
"</body>\n"
"</html>"
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)
print("✅ 완료! (" + str(len(HTML)) + " bytes)")
