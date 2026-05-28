#!/usr/bin/env python3
import anthropic, json, re, time
import yfinance as yf
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
DAYS_KO = ['월','화','수','목','금','토','일']
TODAY_TITLE  = now.strftime("%Y년 %-m월 %-d일") + " (" + DAYS_KO[now.weekday()] + ")"
TODAY_YMD    = now.strftime("%Y-%m-%d")
GENERATED_AT = now.strftime("%Y년 %-m월 %-d일 %H:%M KST")

def get_prev_trading_day(d):
    wd = d.weekday()
    delta = 3 if wd==0 else (2 if wd==6 else (1 if wd==5 else 1))
    return d - timedelta(days=delta)

prev_day   = get_prev_trading_day(now)
PREV_FULL  = prev_day.strftime("%Y년 %-m월 %-d일") + " (" + DAYS_KO[prev_day.weekday()] + ")"
PREV_SHORT = prev_day.strftime("%-m/%-d") + " " + DAYS_KO[prev_day.weekday()]

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

def fmt(v, decimals=2):
    if v is None: return "—"
    return f"{v:,.{decimals}f}"

def chg_str(cur, prev):
    if cur is None or prev is None: return "—"
    diff = cur - prev
    pct  = diff / prev * 100
    sign = "▲" if diff >= 0 else "▼"
    return f"{sign} {diff:+.2f}p ({pct:+.2f}%)"

# ── 1단계: yfinance로 정확한 종가 수집 ──
print("📡 [1/3] yfinance 정확한 종가 수집 중...")

tickers = {
    "kospi":  "^KS11",
    "kosdaq": "^KQ11",
    "sp500":  "^GSPC",
    "nasdaq": "^IXIC",
    "dow":    "^DJI",
    "usd_krw":"KRW=X",
    "wti":    "CL=F",
    "us10y":  "^TNX",
}

mkt = {}
for key, symbol in tickers.items():
    try:
        tk   = yf.Ticker(symbol)
        hist = tk.history(period="5d")
        if len(hist) >= 2:
            mkt[key + "_close"] = round(hist["Close"].iloc[-2], 2)
            mkt[key + "_prev"]  = round(hist["Close"].iloc[-3], 2)
        elif len(hist) == 1:
            mkt[key + "_close"] = round(hist["Close"].iloc[-1], 2)
            mkt[key + "_prev"]  = None
    except Exception as e:
        print(f"  {key} 오류: {e}")

# 등락 계산
kospi_close  = mkt.get("kospi_close");  kospi_prev  = mkt.get("kospi_prev")
kosdaq_close = mkt.get("kosdaq_close"); kosdaq_prev = mkt.get("kosdaq_prev")
sp500_close  = mkt.get("sp500_close");  sp500_prev  = mkt.get("sp500_prev")
nasdaq_close = mkt.get("nasdaq_close"); nasdaq_prev = mkt.get("nasdaq_prev")
dow_close    = mkt.get("dow_close");    dow_prev    = mkt.get("dow_prev")
usd_krw      = mkt.get("usd_krw_close")
wti          = mkt.get("wti_close")
us10y        = mkt.get("us10y_close")

kospi_chg_pt  = round(kospi_close  - kospi_prev,  2) if kospi_close  and kospi_prev  else None
kosdaq_chg_pt = round(kosdaq_close - kosdaq_prev, 2) if kosdaq_close and kosdaq_prev else None
sp500_chg_pt  = round(sp500_close  - sp500_prev,  2) if sp500_close  and sp500_prev  else None
nasdaq_chg_pt = round(nasdaq_close - nasdaq_prev, 2) if nasdaq_close and nasdaq_prev else None
dow_chg_pt    = round(dow_close    - dow_prev,    2) if dow_close    and dow_prev    else None

def pct(cur, prev):
    if cur and prev: return round((cur-prev)/prev*100, 2)
    return None

kospi_chg_pct  = pct(kospi_close,  kospi_prev)
kosdaq_chg_pct = pct(kosdaq_close, kosdaq_prev)
sp500_chg_pct  = pct(sp500_close,  sp500_prev)
nasdaq_chg_pct = pct(nasdaq_close, nasdaq_prev)
dow_chg_pct    = pct(dow_close,    dow_prev)

def chg_display(pt, pc):
    if pt is None or pc is None: return "—"
    sign = "▲" if pt >= 0 else "▼"
    return f"{sign} {pt:+.2f}p ({pc:+.2f}%)"

print(f"  코스피: {fmt(kospi_close)} ({chg_display(kospi_chg_pt, kospi_chg_pct)})")
print(f"  S&P500: {fmt(sp500_close)}")

# banner_title 생성
def make_banner():
    parts = []
    if kospi_chg_pct is not None:
        parts.append(f"코스피 {kospi_chg_pct:+.2f}%")
    if sp500_chg_pct is not None:
        parts.append(f"S&P500 {sp500_chg_pct:+.2f}%")
    return f"전 거래일({PREV_SHORT}) 실제 마감 결과 — " + " · ".join(parts) if parts else f"전 거래일({PREV_SHORT}) 실제 마감 결과"

time.sleep(65)

# ── 2단계: 뉴스 + 일정 + 미국증시 코멘트 ──
print("📰 [2/3] 뉴스·일정 수집 중...")
r2 = safe_json(call_claude(
    "오늘 " + TODAY_YMD + ", 한국 증시 관련 최신 뉴스와 이번주 경제일정을 웹검색으로 수집해 JSON만 반환:\n"
    '{"news":[{"type":"bull","tag":"🇺🇸 미국 증시 (' + PREV_SHORT + ')","title":"헤드라인","desc":"2-3문장 요약"},'
    '{"type":"warn","tag":"📅 이번주 핵심 이벤트","title":"헤드라인","desc":"2-3문장 요약"},'
    '{"type":"neutral","tag":"⚠️ 주요 리스크","title":"헤드라인","desc":"2-3문장 요약"}],'
    '"us_market_comments":{'
    '"sp500":"S&P500 코멘트(예: 8주 연속↑)","nasdaq":"나스닥 코멘트","dow":"다우 코멘트(예: 사상최고치)",'
    '"semicon":"필라델피아반도체 코멘트","wti":"WTI 코멘트","us10y":"금리 코멘트","usd_krw":"환율 코멘트","kospi200f":"코스피200 야간선물 코멘트"},'
    '"schedule":[{"date":"날짜(예:5/28)","today":false,"title":"이벤트명","desc":"설명","imp":"high"},'
    '{"date":"날짜","today":false,"title":"이벤트명","desc":"설명","imp":"med"},'
    '{"date":"날짜","today":false,"title":"이벤트명","desc":"설명","imp":"high"}]}'
))
time.sleep(65)

# ── 3단계: AI 분석 + 업종 + 확률 ──
print("🧠 [3/3] AI 분석 생성 중...")
r3 = safe_json(call_claude(
    "오늘 " + TODAY_YMD + ", 코스피=" + str(kospi_close) + "(" + str(kospi_chg_pct) + "%), S&P500=" + str(sp500_close) + "\n"
    "전일 확정 데이터 기반으로 오늘 한국 증시 전망을 JSON만 반환:\n"
    '{"sentiment":"중립~소폭 강세","sentiment_reason":"전망 근거 한줄",'
    '"kospi_up":58,"kospi_neutral":16,"kosdaq_up":63,"kosdaq_neutral":15,'
    '"kospi_badge":"핵심키워드","kosdaq_badge":"핵심키워드",'
    '"kospi_bear":"범위","kospi_bear_prob":30,"kospi_base":"범위","kospi_base_prob":52,"kospi_bull":"범위","kospi_bull_prob":18,'
    '"kosdaq_bear":"범위","kosdaq_bear_prob":25,"kosdaq_base":"범위","kosdaq_base_prob":55,"kosdaq_bull":"범위","kosdaq_bull_prob":20,'
    '"kospi_base_price":' + str(int(kospi_close) if kospi_close else 7847) + ','
    '"kosdaq_base_price":' + str(int(kosdaq_close) if kosdaq_close else 856) + ','
    '"sectors":[{"name":"반도체","chg":1.5,"note":"이유"},{"name":"2차전지","chg":0.8,"note":"이유"},'
    '{"name":"바이오·제약","chg":0.5,"note":"이유"},{"name":"항공·여행","chg":0.3,"note":"이유"},'
    '{"name":"금융","chg":-0.2,"note":"이유"},{"name":"건설·부동산","chg":-0.5,"note":"이유"},{"name":"유틸리티","chg":-0.8,"note":"이유"}],'
    '"analysis":"오늘 장세 종합 분석 2-3문단 HTML strong 태그 사용",'
    '"tags":[{"type":"bull","text":"키워드"},{"type":"bull","text":"키워드"},{"type":"warn","text":"키워드"},'
    '{"type":"bear","text":"키워드"},{"type":"neutral","text":"키워드"},{"type":"purple","text":"키워드"}]}'
))
print("  센티먼트: " + r3.get('sentiment','—'))

# ── 미국 증시 카드 데이터 조합 (yfinance 수치 + Claude 코멘트) ──
cmts = r2.get('us_market_comments', {})
sp500_cls  = "up" if sp500_chg_pt  and sp500_chg_pt  >= 0 else "down"
nasdaq_cls = "up" if nasdaq_chg_pt and nasdaq_chg_pt >= 0 else "down"
dow_cls    = "up" if dow_chg_pt    and dow_chg_pt    >= 0 else "down"
us_market = [
    {"name":"S&P 500",        "val":fmt(sp500_close),  "chg":(f"{sp500_chg_pct:+.2f}% · " if sp500_chg_pct else "") + cmts.get("sp500",""),  "cls":sp500_cls},
    {"name":"나스닥",          "val":fmt(nasdaq_close), "chg":(f"{nasdaq_chg_pct:+.2f}% · " if nasdaq_chg_pct else "") + cmts.get("nasdaq",""), "cls":nasdaq_cls},
    {"name":"다우존스",        "val":fmt(dow_close),    "chg":(f"{dow_chg_pct:+.2f}% · " if dow_chg_pct else "") + cmts.get("dow",""),    "cls":dow_cls},
    {"name":"필라델피아 반도체","val":"—",               "chg":cmts.get("semicon",""),  "cls":"up"},
    {"name":"WTI 유가",        "val":f"${fmt(wti)}",    "chg":cmts.get("wti",""),      "cls":"neutral"},
    {"name":"미 10년물 금리",  "val":f"{fmt(us10y)}%",  "chg":cmts.get("us10y",""),    "cls":"neutral"},
    {"name":"원/달러 환율",    "val":f"{fmt(usd_krw, 0)}원", "chg":cmts.get("usd_krw",""), "cls":"up"},
    {"name":"코스피200 야간선물","val":"—",              "chg":cmts.get("kospi200f",""),"cls":"neutral"},
]

d = {}
d.update(r2)
d.update(r3)
d['us_market']   = us_market
d['banner_title'] = make_banner()

k_up  = d.get('kospi_up',58);  k_n  = d.get('kospi_neutral',16)
kd_up = d.get('kosdaq_up',63); kd_n = d.get('kosdaq_neutral',15)

# ── 헬퍼 ──
def news_html(lst):
    r = ""
    for n in (lst or [])[:3]:
        t = n.get("type","neutral")
        cls = "bull" if t=="bull" else ("warn" if t=="warn" else "")
        r += ('<div class="news-item ' + cls + '"><div class="news-tag">' + n.get("tag","") + '</div>'
              '<div class="news-title">' + n.get("title","") + '</div>'
              '<div class="news-desc">' + n.get("desc","") + '</div></div>')
    return r

def us_market_html(lst):
    r = ""
    for f in (lst or []):
        r += ('<div class="futures-item"><div class="futures-name">' + f.get("name","") + '</div>'
              '<div class="futures-val ' + f.get("cls","") + '">' + f.get("val","—") + '</div>'
              '<div class="futures-chg ' + f.get("cls","") + '">' + f.get("chg","") + '</div></div>')
    return r

def schedule_html(lst):
    r = ""
    for s in (lst or [])[:5]:
        ic = "sch-high" if s.get("imp")=="high" else "sch-med"
        it = "주요" if s.get("imp")=="high" else "중요"
        td = "<br>오늘" if s.get("today") else ""
        r += ('<div class="schedule-row"><span class="sch-date">' + s.get("date","") + td + '</span>'
              '<div class="sch-content"><div class="sch-title">' + s.get("title","") + ' <span class="sch-badge ' + ic + '">' + it + '</span></div>'
              '<div class="sch-desc">' + s.get("desc","") + '</div></div></div>')
    return r

def tags_html(lst):
    return "".join('<span class="tag tag-' + t.get("type","neutral") + '">' + t.get("text","") + '</span>' for t in (lst or []))

def sectors_js(lst):
    return json.dumps([{"name":s.get("name",""),"chg":s.get("chg",0),"note":s.get("note","")} for s in (lst or [])], ensure_ascii=False)

def gen_chart(base, bear_str, bull_str):
    nb = re.findall(r'[\d]+\.?\d*', (bull_str or "").replace(',',''))
    nd = re.findall(r'[\d]+\.?\d*', (bear_str or "").replace(',',''))
    bh = float(nb[-1]) if nb else base*1.012
    bl = float(nd[0])  if nd else base*0.988
    n = 13
    hi = [round(base+(bh-base)*(i/(n-1)),2) for i in range(n)]
    lo = [round(base+(bl-base)*(i/(n-1)),2) for i in range(n)]
    ba = [(h+l)/2 for h,l in zip(hi,lo)]
    return ba, hi, lo

kb,  kh,  kl  = gen_chart(d.get('kospi_base_price', int(kospi_close) if kospi_close else 7847),  d.get('kospi_bear',''),  d.get('kospi_bull',''))
kdb, kdh, kdl = gen_chart(d.get('kosdaq_base_price', int(kosdaq_close) if kosdaq_close else 856), d.get('kosdaq_bear',''), d.get('kosdaq_bull',''))

HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>한국 주식시장 AI 대시보드 | """ + TODAY_TITLE + """</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
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
  .result-banner { background: linear-gradient(135deg, #043B72 0%, #1d5fa8 100%); border-radius: 12px; padding: 14px 20px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(4,59,114,0.2); }
  .result-banner h3 { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.7); margin-bottom: 10px; }
  .result-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .result-item { text-align: center; }
  .result-label { font-size: 10px; color: rgba(255,255,255,0.6); margin-bottom: 3px; }
  .result-val { font-size: 17px; font-weight: 700; color: #fca5a5; }
  .result-chg { font-size: 11px; color: rgba(255,255,255,0.75); margin-top: 2px; }
  .news-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
  .news-item { background: #fff; border-radius: 10px; padding: 12px 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); border-left: 3px solid #2563eb; }
  .news-item.bull { border-left-color: #dc2626; } .news-item.warn { border-left-color: #d97706; }
  .news-tag { font-size: 10px; font-weight: 700; color: #2563eb; margin-bottom: 4px; }
  .news-item.bull .news-tag { color: #dc2626; } .news-item.warn .news-tag { color: #d97706; }
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
  .up { color: #dc2626; } .down { color: #2563eb; } .neutral { color: #888; } .warn { color: #d97706; }
  .badge { font-size: 10px; padding: 2px 8px; border-radius: 99px; font-weight: 600; }
  .badge-up { background: #fee2e2; color: #b91c1c; } .badge-warn { background: #fef3c7; color: #92400e; }
  .badge-blue { background: #dbeafe; color: #1d4ed8; } .badge-green { background: #d1fae5; color: #065f46; }
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
  .sch-high { background: #fee2e2; color: #b91c1c; } .sch-med { background: #fef3c7; color: #92400e; }
  .analysis-text { font-size: 13px; line-height: 1.8; color: #333; }
  .tags { margin-top: 10px; }
  .tag { display: inline-block; font-size: 11px; padding: 2px 9px; border-radius: 99px; margin: 2px 3px 2px 0; }
  .tag-bull { background: #fee2e2; color: #b91c1c; } .tag-bear { background: #dbeafe; color: #1d4ed8; }
  .tag-neutral { background: #f3f4f6; color: #555; } .tag-warn { background: #fef3c7; color: #92400e; }
  .tag-purple { background: #ede9fe; color: #5b21b6; }
  .notice { font-size: 11px; color: #999; background: #f9fafb; border-radius: 8px; padding: 9px 12px; margin-top: 12px; border: 1px solid #e5e7eb; }
  .chart-wrap { position: relative; height: 165px; }
  .footer { text-align: center; margin-top: 20px; font-size: 11px; color: #bbb; padding-bottom: 16px; }
  @media(max-width:768px) { .grid-4{grid-template-columns:repeat(2,1fr)} .grid-2{grid-template-columns:1fr} .news-row{grid-template-columns:1fr} .result-grid{grid-template-columns:repeat(2,1fr)} }
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
      <span class="mw-date">""" + TODAY_TITLE + """</span>
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
          <span class="mw-s-val">""" + d.get('sentiment','—') + """</span>
        </div>
        <div class="mw-kpi-row">
          <div class="mw-kpi"><div class="mw-kpi-val">""" + fmt(kospi_close) + """</div><div class="mw-kpi-label">코스피 전일(""" + PREV_SHORT + """)</div></div>
          <div class="mw-kpi-div"></div>
          <div class="mw-kpi"><div class="mw-kpi-val">""" + (f"{kospi_chg_pct:+.2f}%" if kospi_chg_pct else "—") + """</div><div class="mw-kpi-label">전일 등락</div></div>
          <div class="mw-kpi-div"></div>
          <div class="mw-kpi"><div class="mw-kpi-val">""" + fmt(kosdaq_close) + """</div><div class="mw-kpi-label">코스닥 전일</div></div>
        </div>
      </div>
    </div>
    <div class="mw-bottom-bar">
      <div class="mw-sources">
        <span class="mw-src-label">데이터 소스</span>
        <span class="mw-pill">Yahoo Finance</span><span class="mw-pill">KRX</span><span class="mw-pill">뉴스 검색</span><span class="mw-pill">야간선물</span>
      </div>
      <span class="mw-update">AI 생성: """ + GENERATED_AT + """ | 기준: """ + PREV_FULL + """</span>
    </div>
    <div class="mw-orange-line"></div>
  </div>

  <div class="result-banner">
    <h3>📌 """ + d.get('banner_title','전 거래일 실제 마감 결과') + """</h3>
    <div class="result-grid">
      <div class="result-item"><div class="result-label">코스피 종가</div><div class="result-val">""" + fmt(kospi_close) + """</div><div class="result-chg">""" + chg_display(kospi_chg_pt, kospi_chg_pct) + """</div></div>
      <div class="result-item"><div class="result-label">S&amp;P 500 (""" + PREV_SHORT + """)</div><div class="result-val">""" + fmt(sp500_close) + """</div><div class="result-chg">""" + chg_display(sp500_chg_pt, sp500_chg_pct) + """</div></div>
      <div class="result-item"><div class="result-label">나스닥</div><div class="result-val">""" + fmt(nasdaq_close) + """</div><div class="result-chg">""" + chg_display(nasdaq_chg_pt, nasdaq_chg_pct) + """</div></div>
      <div class="result-item"><div class="result-label">다우존스</div><div class="result-val">""" + fmt(dow_close) + """</div><div class="result-chg">""" + chg_display(dow_chg_pt, dow_chg_pct) + """</div></div>
    </div>
  </div>

  <div class="news-row">""" + news_html(d.get('news',[])) + """</div>

  <div class="grid-4">
    <div class="metric-card"><div class="metric-label">코스피 전일 종가 (""" + PREV_SHORT + """)</div><div class="metric-value up">""" + fmt(kospi_close) + """</div><div class="metric-sub up">""" + chg_display(kospi_chg_pt, kospi_chg_pct) + """</div></div>
    <div class="metric-card"><div class="metric-label">코스닥 전일 종가</div><div class="metric-value up">""" + fmt(kosdaq_close) + """</div><div class="metric-sub up">""" + chg_display(kosdaq_chg_pt, kosdaq_chg_pct) + """</div></div>
    <div class="metric-card"><div class="metric-label">오늘 시장 센티먼트</div><div class="metric-value warn">""" + d.get('sentiment','—') + """</div><div class="metric-sub warn">""" + d.get('sentiment_reason','') + """</div></div>
    <div class="metric-card"><div class="metric-label">원/달러 환율 (""" + PREV_SHORT + """)</div><div class="metric-value up">""" + (f"{fmt(usd_krw, 0)}원" if usd_krw else "—") + """</div><div class="metric-sub up">Yahoo Finance 실측</div></div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">📊 코스피 상승/하락 확률 <span class="badge badge-warn">""" + d.get('kospi_badge','') + """</span></div>
      <div class="gauge-wrap">
        <div class="gauge-bar-outer">
          <div class="gauge-up-fill" style="width:""" + str(k_up) + """%;background:linear-gradient(90deg,#fca5a5,#dc2626);"><span class="gauge-bar-label">""" + str(k_up) + """%</span></div>
          <div class="gauge-down-fill" style="background:linear-gradient(90deg,#93c5fd,#2563eb);"><span class="gauge-bar-label">""" + str(100-k_up) + """%</span></div>
          <div class="gauge-center-line"></div>
        </div>
        <div class="gauge-labels"><span class="gauge-label-up">▲ 상승 """ + str(k_up) + """%</span><span class="gauge-label-center">50%</span><span class="gauge-label-down">하락 """ + str(100-k_up) + """% ▼</span></div>
      </div>
      <div class="prob-divider">— 시나리오별 확률 —</div>
      <div class="prob-row"><span class="prob-name up">추가 상승</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:""" + str(k_up) + """%;background:linear-gradient(90deg,#ef4444,#dc2626);"><span style="font-size:10px;font-weight:700;color:#fff;">""" + str(k_up) + """%</span></div></div><span class="prob-pct up">""" + str(k_up) + """%</span></div>
      <div class="prob-row"><span class="prob-name neutral">횡보</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:""" + str(k_n) + """%;background:#9ca3af;"><span style="font-size:10px;font-weight:700;color:#fff;">""" + str(k_n) + """%</span></div></div><span class="prob-pct neutral">""" + str(k_n) + """%</span></div>
      <div class="prob-row"><span class="prob-name down">차익 하락</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:""" + str(100-k_up-k_n) + """%;background:linear-gradient(90deg,#3b82f6,#2563eb);"><span style="font-size:10px;font-weight:700;color:#fff;">""" + str(100-k_up-k_n) + """%</span></div></div><span class="prob-pct down">""" + str(100-k_up-k_n) + """%</span></div>
    </div>
    <div class="card">
      <div class="card-title">📊 코스닥 상승/하락 확률 <span class="badge badge-green">""" + d.get('kosdaq_badge','') + """</span></div>
      <div class="gauge-wrap">
        <div class="gauge-bar-outer">
          <div class="gauge-up-fill" style="width:""" + str(kd_up) + """%;background:linear-gradient(90deg,#fca5a5,#dc2626);"><span class="gauge-bar-label">""" + str(kd_up) + """%</span></div>
          <div class="gauge-down-fill" style="background:linear-gradient(90deg,#93c5fd,#2563eb);"><span class="gauge-bar-label">""" + str(100-kd_up) + """%</span></div>
          <div class="gauge-center-line"></div>
        </div>
        <div class="gauge-labels"><span class="gauge-label-up">▲ 상승 """ + str(kd_up) + """%</span><span class="gauge-label-center">50%</span><span class="gauge-label-down">하락 """ + str(100-kd_up) + """% ▼</span></div>
      </div>
      <div class="prob-divider">— 시나리오별 확률 —</div>
      <div class="prob-row"><span class="prob-name up">추가 상승</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:""" + str(kd_up) + """%;background:linear-gradient(90deg,#ef4444,#dc2626);"><span style="font-size:10px;font-weight:700;color:#fff;">""" + str(kd_up) + """%</span></div></div><span class="prob-pct up">""" + str(kd_up) + """%</span></div>
      <div class="prob-row"><span class="prob-name neutral">횡보</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:""" + str(kd_n) + """%;background:#9ca3af;"><span style="font-size:10px;font-weight:700;color:#fff;">""" + str(kd_n) + """%</span></div></div><span class="prob-pct neutral">""" + str(kd_n) + """%</span></div>
      <div class="prob-row"><span class="prob-name down">하락</span><div class="prob-bar-bg"><div class="prob-bar-inner" style="width:""" + str(100-kd_up-kd_n) + """%;background:linear-gradient(90deg,#3b82f6,#2563eb);"><span style="font-size:10px;font-weight:700;color:#fff;">""" + str(100-kd_up-kd_n) + """%</span></div></div><span class="prob-pct down">""" + str(100-kd_up-kd_n) + """%</span></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">📈 코스피 장중 예상 <span class="badge badge-warn">""" + d.get('kospi_badge','') + """</span></div>
      <div class="pred-band">
        <div class="pred-item pred-bear"><div class="pred-label">약세</div><div class="pred-range down">""" + d.get('kospi_bear','—') + """</div><div class="pred-prob">""" + str(d.get('kospi_bear_prob','—')) + """%</div></div>
        <div class="pred-item pred-base"><div class="pred-label">기본</div><div class="pred-range">""" + d.get('kospi_base','—') + """</div><div class="pred-prob">""" + str(d.get('kospi_base_prob','—')) + """%</div></div>
        <div class="pred-item pred-bull"><div class="pred-label">강세</div><div class="pred-range up">""" + d.get('kospi_bull','—') + """</div><div class="pred-prob">""" + str(d.get('kospi_bull_prob','—')) + """%</div></div>
      </div>
      <div class="chart-wrap"><canvas id="kospiChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">📈 코스닥 장중 예상 <span class="badge badge-green">""" + d.get('kosdaq_badge','') + """</span></div>
      <div class="pred-band">
        <div class="pred-item pred-bear"><div class="pred-label">약세</div><div class="pred-range down">""" + d.get('kosdaq_bear','—') + """</div><div class="pred-prob">""" + str(d.get('kosdaq_bear_prob','—')) + """%</div></div>
        <div class="pred-item pred-base"><div class="pred-label">기본</div><div class="pred-range">""" + d.get('kosdaq_base','—') + """</div><div class="pred-prob">""" + str(d.get('kosdaq_base_prob','—')) + """%</div></div>
        <div class="pred-item pred-bull"><div class="pred-label">강세</div><div class="pred-range up">""" + d.get('kosdaq_bull','—') + """</div><div class="pred-prob">""" + str(d.get('kosdaq_bull_prob','—')) + """%</div></div>
      </div>
      <div class="chart-wrap"><canvas id="kosdaqChart"></canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">🌍 전 거래일 미국 증시 &amp; 주요 지표 (""" + PREV_SHORT + """)</div>
      <div class="futures-grid">""" + us_market_html(us_market) + """</div>
    </div>
    <div class="card">
      <div class="card-title">📅 이번 주 주요 경제 일정</div>
      """ + schedule_html(d.get('schedule',[])) + """
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">🏦 오늘 업종 예상</div>
      <div id="sectorList"></div>
    </div>
    <div class="card">
      <div class="card-title">🧠 AI 종합 분석</div>
      <div class="analysis-text">""" + d.get('analysis','분석 데이터를 불러오는 중 오류가 발생했습니다.') + """</div>
      <div class="tags">""" + tags_html(d.get('tags',[])) + """</div>
      <div class="notice">⚠️ 종가 데이터는 Yahoo Finance 실측값 기준이며, 분석은 AI 참고용입니다. 실제 투자 판단의 근거로 사용하지 마세요.</div>
    </div>
  </div>

  <div class="footer">MIRAE ASSET Market Intelligence · 한국 주식시장 AI 대시보드 · """ + TODAY_TITLE + """ · 데이터: Yahoo Finance · 참고용</div>
</div>

<script>
const labels = ['9:00','9:30','10:00','10:30','11:00','11:30','12:00','13:00','13:30','14:00','14:30','15:00','15:30'];
function makeChart(id, base, high, low, color) {
  new Chart(document.getElementById(id).getContext('2d'), {
    type:'line',
    data:{ labels, datasets:[
      {label:'상단',data:high,borderColor:color,borderWidth:1,borderDash:[4,3],fill:false,tension:0.4,pointRadius:0},
      {label:'기본',data:base,borderColor:color,borderWidth:2.5,fill:false,tension:0.4,pointRadius:3,pointBackgroundColor:color},
      {label:'하단',data:low,borderColor:color,borderWidth:1,borderDash:[4,3],fill:'-1',backgroundColor:color+'14',tension:0.4,pointRadius:0}
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{mode:'index',intersect:false,callbacks:{label:c=>c.dataset.label+': '+c.parsed.y.toLocaleString()}}},
      scales:{x:{grid:{display:false},ticks:{font:{size:10},maxRotation:0,maxTicksLimit:7}},y:{grid:{color:'rgba(0,0,0,0.04)'},ticks:{font:{size:10},callback:v=>v.toLocaleString()}}}
    }
  });
}
makeChart('kospiChart',  """ + json.dumps(kb)  + """, """ + json.dumps(kh)  + """, """ + json.dumps(kl)  + """, '#dc2626');
makeChart('kosdaqChart', """ + json.dumps(kdb) + """, """ + json.dumps(kdh) + """, """ + json.dumps(kdl) + """, '#2563eb');

const sectors = """ + sectors_js(d.get('sectors',[])) + """;
const maxAbs = Math.max(...sectors.map(s=>Math.abs(s.chg)));
document.getElementById('sectorList').innerHTML = sectors.map(s=>{
  const pct = Math.abs(s.chg)/maxAbs*100;
  const col = s.chg>0?'#dc2626':'#2563eb';
  const cls = s.chg>0?'up':'down';
  return `<div class="sector-row"><span class="sector-name">${s.name}</span><div class="sector-bar-bg"><div class="sector-bar" style="width:${pct.toFixed(0)}%;background:${col};"></div></div><span class="sector-pct ${cls}">${s.chg>0?'+':''}${s.chg.toFixed(1)}%</span></div>`;
}).join('');
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)
print("✅ 완료! (" + str(len(HTML)) + " bytes)")
