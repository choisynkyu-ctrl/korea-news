"""날짜별 JSON으로 대시보드 HTML을 만든다 (시세 타일 · 관심 종목 · 뉴스 TOP 10)."""
import json
from collections import Counter
from datetime import date
from html import escape

from .config import ARCHIVE_DIR, CATEGORIES, DATA_DIR, DOCS

WEEKDAYS = "월화수목금토일"

CAT_COLORS = {
    "정치": "#3b6fd9",
    "경제/정책": "#1f9d6b",
    "증시/금융": "#c2410c",
    "산업/기업": "#7a4fd6",
    "부동산": "#a16207",
    "사회": "#b8478f",
    "IT/과학": "#2f9bb0",
    "국제/외교": "#4f6b8a",
    "기타": "#6b7280",
}

# 국내 관례: 상승 빨강 · 하락 파랑 (항상 ▲▼ 기호와 함께 표시해 색만으로 구분하지 않음)
CSS = """
:root{--bg:#f5f6f8;--card:#fff;--text:#16181d;--muted:#606773;--line:#e3e6eb;--accent:#16181d;--chip:#eef0f3;--up:#d42b36;--down:#1d5fd1;--flat:#6b7280;--up-fill:rgba(212,43,54,.08);--down-fill:rgba(29,95,209,.08)}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b21;--text:#eceef2;--muted:#9aa1ad;--line:#2a2e36;--accent:#eceef2;--chip:#22262e;--up:#ff6b72;--down:#6aa5ff;--flat:#9aa1ad;--up-fill:rgba(255,107,114,.10);--down-fill:rgba(106,165,255,.10)}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Pretendard,-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:32px 16px 64px}
header{margin-bottom:8px}
.eyebrow{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-size:30px;line-height:1.25;margin:6px 0 10px;letter-spacing:-.02em}
.digest{margin:16px 0 0;display:grid;gap:10px;max-width:860px}
.digest .row{display:grid;grid-template-columns:64px 1fr;gap:12px;align-items:baseline}
.digest .lbl{font-size:12px;font-weight:700;text-align:center;background:var(--chip);border-radius:6px;padding:3px 0}
.digest p{margin:0;font-size:15px}
.digest .row:first-child p{font-size:17px;font-weight:600}
.digest .span{font-size:12px;color:var(--muted);margin-left:6px;white-space:nowrap}
nav.days{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
nav.days a{font-size:13px;color:var(--muted);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:4px 12px}
nav.days a:hover{color:var(--text);border-color:var(--muted)}
h2.sec{font-size:20px;margin:36px 0 12px;letter-spacing:-.01em;display:flex;align-items:baseline;gap:10px}
h2.sec small{font-size:12px;font-weight:500;color:var(--muted)}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
@media (max-width:860px){.tiles{grid-template-columns:repeat(3,minmax(0,1fr))}}
.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px 10px;display:flex;flex-direction:column;gap:2px;min-width:0}
.tile .grp{font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.02em}
.tile .nm{font-size:14px;font-weight:600}
.tile .px{font-size:24px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.3}
.chg{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--flat)}
.spark{position:relative;margin-top:6px}
.spark svg{display:block;width:100%;height:44px;overflow:visible}
.spark .tip{position:absolute;top:-2px;right:0;font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums;background:var(--card);padding:0 2px}
.spark .tip:empty{display:none}
.spark .guide{stroke:var(--muted);stroke-width:1;opacity:0}
.spark:hover .guide{opacity:.5}
.tile .foot{display:flex;justify-content:space-between;gap:6px;font-size:12px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:2px}
.comment{margin:12px 0 0;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:grid;grid-template-columns:52px 1fr;gap:12px;align-items:baseline}
.comment .lbl{font-size:12px;font-weight:700;text-align:center;background:var(--chip);border-radius:6px;padding:3px 0}
.comment p{margin:0;font-size:15px}
.tablewrap{margin-top:12px;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
th,td{padding:10px 14px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
th{font-size:12px;font-weight:600;color:var(--muted);cursor:pointer;user-select:none}
th[aria-sort=descending]::after{content:" ↓"}th[aria-sort=ascending]::after{content:" ↑"}
th:first-child,td:first-child{text-align:left}
td .code{font-size:11px;color:var(--muted);margin-left:6px}
td .no{display:inline-block;min-width:20px;font-size:12px;font-weight:700;color:var(--muted)}
th:first-child,td:first-child{position:sticky;left:0;background:var(--card);z-index:1}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 4px}
.tabs button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:999px;padding:6px 14px;cursor:pointer}
.tabs button[aria-pressed=true]{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.empty{color:var(--muted);font-size:14px}
td.sp{width:150px;padding-top:4px;padding-bottom:4px}
td.sp .spark{margin:0}td.sp .spark svg{height:28px}td.sp .tip{display:none}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px}
.filters button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:999px;padding:6px 14px;cursor:pointer}
.filters button[aria-pressed=true]{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.filters .n{opacity:.6;margin-left:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:10px}
.card.top{grid-column:1/-1}
.card.top h3{font-size:24px}
.meta{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);flex-wrap:wrap}
.rank{font-weight:800;font-size:15px;color:var(--text);min-width:22px}
.cat{font-weight:600;padding:2px 8px;border-radius:6px;color:#fff}
h3{font-size:18px;line-height:1.4;margin:0;letter-spacing:-.01em}
.summary{margin:0;font-size:15px}
.why{margin:0;font-size:14px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px}
.related{display:flex;gap:6px;flex-wrap:wrap;font-size:12px}
.related span{border:1px solid var(--line);border-radius:6px;padding:1px 8px}
.related span::before{content:"# ";color:var(--muted)}
.sources{display:flex;gap:6px;flex-wrap:wrap;margin-top:auto;padding-top:6px}
.sources a{font-size:12px;color:var(--muted);background:var(--chip);border-radius:6px;padding:3px 8px;text-decoration:none}
.sources a:hover{color:var(--text)}
footer{margin-top:40px;font-size:12px;color:var(--muted)}
@media (max-width:520px){h1{font-size:24px}.grid{grid-template-columns:1fr}.card.top h3{font-size:20px}
.digest .row,.comment{grid-template-columns:1fr;gap:4px}.digest .lbl,.comment .lbl{justify-self:start;padding:2px 8px}
.tiles{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.tile{padding:12px}.tile .px{font-size:19px}
td.sp{width:96px}th,td{padding:9px 10px}}
"""

JS = """
const btns=document.querySelectorAll('.filters button');
btns.forEach(b=>b.addEventListener('click',()=>{
  btns.forEach(x=>x.setAttribute('aria-pressed',x===b));
  const c=b.dataset.cat;
  document.querySelectorAll('.card').forEach(el=>{el.hidden=!(c==='all'||el.dataset.cat===c)});
}));
// 추이 그래프 hover: 날짜·값 표시
document.querySelectorAll('.spark').forEach(sp=>{
  const pts=JSON.parse(sp.dataset.p),dec=+sp.dataset.dec,tip=sp.querySelector('.tip'),g=sp.querySelector('.guide'),svg=sp.querySelector('svg');
  if(!tip)return;
  const fmt=v=>v.toLocaleString('ko-KR',{minimumFractionDigits:dec,maximumFractionDigits:dec});
  const def=tip.textContent;
  sp.addEventListener('mousemove',e=>{
    const r=svg.getBoundingClientRect(),i=Math.max(0,Math.min(pts.length-1,Math.round((e.clientX-r.left)/r.width*(pts.length-1))));
    const x=pts.length<2?0:i/(pts.length-1)*200;g.setAttribute('x1',x);g.setAttribute('x2',x);
    const [d,v]=pts[i];tip.textContent=d.slice(5).replace('-','/')+'  '+fmt(v);
  });
  sp.addEventListener('mouseleave',()=>{tip.textContent=def});
});
// 업종 버튼
const tabs=document.querySelectorAll('.tabs button');
function showGroup(g){tabs.forEach(x=>x.setAttribute('aria-pressed',x.dataset.g===g));document.querySelectorAll('.group').forEach(p=>{p.hidden=p.dataset.g!==g});}
tabs.forEach(b=>b.addEventListener('click',()=>{showGroup(b.dataset.g);try{localStorage.setItem('kb-group',b.textContent)}catch(e){}}));
try{const saved=localStorage.getItem('kb-group');const t=[...tabs].find(x=>x.textContent===saved);if(t)showGroup(t.dataset.g)}catch(e){}
// 종목 표 정렬
document.querySelectorAll('table.sortable').forEach(t=>{
  t.querySelectorAll('th[data-k]').forEach((th,ci)=>th.addEventListener('click',()=>{
    const k=th.dataset.k,cur=th.getAttribute('aria-sort'),desc=k==='rank'?cur==='ascending':cur!=='descending',tb=t.tBodies[0];
    t.querySelectorAll('th').forEach(x=>x.removeAttribute('aria-sort'));th.setAttribute('aria-sort',desc?'descending':'ascending');
    [...tb.rows].sort((a,b)=>{const x=a.dataset[k],y=b.dataset[k];const r=(x===''||y==='')?(x===''?-1:1):isNaN(x)?x.localeCompare(y,'ko'):x-y;return desc?-r:r}).forEach(r=>tb.appendChild(r));
  }));
});
"""


def _date_label(d: date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def _dir(v: float) -> str:
    return "up" if v > 0 else "down" if v < 0 else "flat"


def _arrow(v: float) -> str:
    return "▲" if v > 0 else "▼" if v < 0 else "–"


def _num(v: float, dec: int) -> str:
    return f"{v:,.{dec}f}"


def _spark(points: list, dec: int, direction: str, tip: str = "") -> str:
    """1년 종가 추이 (단일 계열이라 범례 없음). 폭 200 기준 좌표, hover로 날짜·값 표시."""
    vals = [v for _, v in points]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    h, pad = 44, 3
    xy = [(i / (len(vals) - 1) * 200, pad + (hi - v) / span * (h - 2 * pad)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    area = f"0,{h} {line} 200,{h}"
    lx, _ = xy[-1]
    return (
        f'<div class="spark" data-p="{escape(json.dumps(points))}" data-dec="{dec}">'
        f'<span class="tip">{escape(tip)}</span>'
        f'<svg viewBox="0 0 200 {h}" preserveAspectRatio="none" role="img" aria-label="최근 1년 추이, 최저 {_num(lo, dec)} 최고 {_num(hi, dec)}">'
        f'<polygon points="{area}" fill="var(--{direction}-fill)"/>'
        f'<polyline points="{line}" fill="none" stroke="var(--{direction})" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        f'<line class="guide" x1="{lx:.1f}" x2="{lx:.1f}" y1="0" y2="{h}" vector-effect="non-scaling-stroke"/>'
        "</svg></div>"
    )


def _trend(q: dict) -> float:
    """그래프 색을 정할 기간 수익률 (예전 데이터는 period_pct)."""
    return q.get("y1_pct", q.get("period_pct", 0)) or 0


def _ret(v, label: str = "") -> str:
    if v is None:
        return f'<span class="flat">{label} -</span>' if label else '<span class="flat">-</span>'
    return f'<span class="{_dir(v)}">{label + " " if label else ""}{v:+.2f}%</span>'


def _cap(eok) -> str:
    if not eok:
        return "-"
    return f"{eok / 10000:,.1f}조" if eok >= 10000 else f"{eok:,}억"


def _tile(q: dict) -> str:
    dec = q.get("decimals", 2)
    m1 = q.get("m1_pct", q.get("period_pct"))
    return f"""<div class="tile">
  <span class="grp">{escape(q['group'])}</span>
  <span class="nm">{escape(q['name'])}</span>
  <span class="px">{_num(q['price'], dec)}</span>
  <span class="chg {_dir(q['change'])}">{_arrow(q['change'])} {_num(abs(q['change']), dec)} ({q['change_pct']:+.2f}%)</span>
  {_spark(q['spark'], dec, _dir(_trend(q)))}
  <div class="foot">{_ret(m1, '1개월')}{_ret(q.get('q1_pct'), '분기')}</div>
</div>"""


def _stocks_table(stocks: list[dict], caption: str) -> str:
    if not stocks:
        return '<p class="empty">시세를 받지 못했습니다.</p>'
    num = lambda v: "" if v is None else v
    rows = "".join(
        f'<tr data-rank="{i}" data-name="{escape(s["name"])}" data-price="{s["price"]}" data-chg="{s["change_pct"]}" '
        f'data-m1="{num(s.get("m1_pct", s.get("period_pct")))}" data-q1="{num(s.get("q1_pct"))}" data-cap="{s.get("cap") or 0}">'
        f'<td><span class="no">{i}</span>{escape(s["name"])}<span class="code">{escape(s["code"])}</span></td>'
        f'<td>{_num(s["price"], 0)}</td>'
        f'<td class="{_dir(s["change"])}">{_arrow(s["change"])} {abs(s["change_pct"]):.2f}%</td>'
        f'<td>{_ret(s.get("m1_pct", s.get("period_pct")))}</td>'
        f'<td>{_ret(s.get("q1_pct"))}</td>'
        f'<td>{_cap(s.get("cap"))}</td>'
        f'<td class="sp">{_spark(s["spark"], 0, _dir(_trend(s)))}</td></tr>'
        for i, s in enumerate(stocks, start=1)
    )
    return f"""<div class="tablewrap"><table class="sortable">
<caption hidden>{escape(caption)}</caption>
<thead><tr><th data-k="rank">종목</th><th data-k="price">종가(원)</th><th data-k="chg">전일 대비</th><th data-k="m1">1개월</th><th data-k="q1">분기</th><th data-k="cap">시가총액</th><th>1년 추이</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""


def _groups_html(m: dict) -> str:
    groups = m.get("groups")
    if not groups and m.get("stocks"):          # 예전 데이터: 관심 종목 한 묶음
        groups = [{"name": "관심 종목", "stocks": m["stocks"]}]
    if not groups:
        return ""
    tabs = "".join(
        f'<button data-g="{i}" aria-pressed="{str(i == 0).lower()}">{escape(g["name"])}</button>'
        for i, g in enumerate(groups)
    )
    panels = "".join(
        f'<div class="group" data-g="{i}"{"" if i == 0 else " hidden"}>{_stocks_table(g["stocks"], g["name"] + " 시가총액 상위")}</div>'
        for i, g in enumerate(groups)
    )
    return f"""<h2 class="sec">업종별 TOP {max(len(g['stocks']) for g in groups)}<small>시가총액 순 · 버튼으로 업종 선택 · 머리글을 누르면 정렬</small></h2>
<div class="tabs" role="group" aria-label="업종 선택">{tabs}</div>
{panels}"""


def _market_html(data: dict) -> str:
    m = data.get("market") or {}
    if not m.get("indices") and not m.get("groups") and not m.get("stocks"):
        return ""
    tiles = "".join(_tile(q) for q in m.get("indices", []))
    comment = data.get("market_comment", "")
    comment_html = f'<div class="comment"><span class="lbl">시황</span><p>{escape(comment)}</p></div>' if comment else ""
    return f"""<h2 class="sec">시장<small>전일 종가 기준 · 해외는 최근 마감 · 그래프는 최근 1년</small></h2>
<div class="tiles">{tiles}</div>
{comment_html}
{_groups_html(m)}"""


def _card(s: dict) -> str:
    color = CAT_COLORS.get(s["category"], "#6b7280")
    uniq = list({src["name"]: src for src in reversed(s.get("sources", []))}.values())[::-1][:6]
    sources = "".join(
        f'<a href="{escape(src["link"])}" target="_blank" rel="noopener" title="{escape(src["title"])}">{escape(src["name"])}</a>'
        for src in uniq
    )
    related = "".join(f"<span>{escape(r)}</span>" for r in s.get("related", [])[:3])
    cls = "card top" if s["rank"] == 1 else "card"
    outlets = f'<span title="이 이슈를 보도한 주요 언론사 수">주요 언론 {s["outlets"]}곳</span>' if s.get("outlets") else ""
    return f"""<article class="{cls}" data-cat="{escape(s['category'])}">
  <div class="meta"><span class="rank">{s['rank']:02d}</span><span class="cat" style="background:{color}">{escape(s['category'])}</span>{outlets}</div>
  <h3>{escape(s['title'])}</h3>
  <p class="summary">{escape(s['summary'])}</p>
  <p class="why">{escape(s['why_it_matters'])}</p>
  {f'<div class="related" aria-label="관련 업종·종목">{related}</div>' if related else ''}
  <div class="sources">{sources}</div>
</article>"""


def _digest_html(data: dict) -> str:
    rows = [("일간", data.get("headline_of_day", ""), "")]
    dg = data.get("digest") or {}
    for key, label, span in (("weekly", "주간", 7), ("monthly", "월간", 30)):
        if key in dg:
            n = dg[key]["days"]
            note = f"최근 {span}일" + (f" 중 {n}일치" if n < span else "")
            rows.append((label, dg[key]["text"], note))
    body = "".join(
        f'<div class="row"><span class="lbl">{lbl}</span><p>{escape(text)}'
        + (f'<span class="span">{note}</span>' if note else "") + "</p></div>"
        for lbl, text, note in rows if text
    )
    return f'<section class="digest" aria-label="뉴스 흐름 요약">{body}</section>'


def render_page(data: dict, d: date, root: str, all_dates: list[date]) -> str:
    counts = Counter(s["category"] for s in data["stories"])
    filters = f'<button data-cat="all" aria-pressed="true">전체<span class="n">{len(data["stories"])}</span></button>' + "".join(
        f'<button data-cat="{escape(c)}" aria-pressed="false">{escape(c)}<span class="n">{counts[c]}</span></button>'
        for c in CATEGORIES if counts[c]
    )
    days = "".join(
        f'<a href="{root}archive/{x.isoformat()}.html">{x.month}/{x.day}</a>'
        for x in sorted(all_dates, reverse=True)[:14] if x != d
    )
    days_html = f'<nav class="days"><a href="{root}index.html">최신</a>{days}</nav>'
    cards = "\n".join(_card(s) for s in data["stories"])
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>국내 뉴스 · 증시 · {d.month}/{d.day}</title>
<meta property="og:title" content="국내 뉴스 · 증시 브리핑 · {_date_label(d)}">
<meta property="og:description" content="{escape(data.get('headline_of_day', ''))}">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.min.css">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">Korea Briefing · {_date_label(d)}</div>
  <h1>오늘의 국내 뉴스 · 증시</h1>
  {_digest_html(data)}
  {days_html}
</header>
{_market_html(data)}
<h2 class="sec">주요 뉴스 TOP {len(data['stories'])}</h2>
<div class="filters">{filters}</div>
<main class="grid">
{cards}
</main>
<footer>연합뉴스, 한겨레, 경향신문, 동아일보, 조선일보, 매일경제, SBS, JTBC, Google News(종합·경제) RSS를 바탕으로 AI(Google Gemini)가 선정·요약했습니다.
시세는 Yahoo Finance 일별 종가, 시가총액·종목 정보는 네이버 증권 기준이며 지연·오차가 있을 수 있습니다. 투자 판단의 근거로 쓰지 마시고, 정확한 내용은 원문과 공식 시세를 확인하세요.</footer>
</div>
<script>{JS}</script>
</body>
</html>"""


def save_and_render(data: dict, d: date) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    data = {**data, "date": d.isoformat()}
    for name in (f"{d.isoformat()}.json", "latest.json"):
        (DATA_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    render_all()


def render_all() -> None:
    files = sorted(p for p in DATA_DIR.glob("????-??-??.json"))
    all_dates = [date.fromisoformat(p.stem) for p in files]
    for p, d in zip(files, all_dates):
        data = json.loads(p.read_text(encoding="utf-8"))
        (ARCHIVE_DIR / f"{d.isoformat()}.html").write_text(
            render_page(data, d, "../", all_dates), encoding="utf-8")
    if files:
        latest = json.loads(files[-1].read_text(encoding="utf-8"))
        (DOCS / "index.html").write_text(
            render_page(latest, all_dates[-1], "", all_dates), encoding="utf-8")
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / ".nojekyll").touch()
    print(f"[render] {len(files)}개 날짜 페이지 생성")
