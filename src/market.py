"""지수·환율·업종별 종목 시세를 모은다.
- 시세: Yahoo Finance 공개 차트 API (1년 일별 종가)
- 종목 이름·코스피/코스닥 구분·시가총액: 네이버 증권 모바일 API (실패하면 config 이름, .KS→.KQ 순으로 시도)
"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import requests

from .config import ALL_GROUP, CHART_RANGE, INDICES, PERIOD_RETURNS, QUARTERS, SCALE, STOCK_GROUPS, TOP_N

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
NAVER = "https://m.stock.naver.com/api/stock/{code}/{kind}"
UA = {"User-Agent": "Mozilla/5.0 (daily-korea-briefing)"}

INDEX_POINTS = 130   # 그래프에 저장할 최대 점 수 (1년 ≈ 250거래일을 솎아 HTML·JSON 크기를 줄임)
STOCK_POINTS = 60


def _series(symbol: str) -> list[tuple[str, float]]:
    """[(YYYY-MM-DD, 종가), ...] 오래된 순. 날짜는 거래소 현지 기준, 빈 값(None)은 뺀다."""
    r = requests.get(CHART.format(symbol=symbol), params={"range": CHART_RANGE, "interval": "1d"},
                     headers=UA, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    closes = res["indicators"]["quote"][0]["close"]
    k = SCALE.get(symbol, 1)
    meta = res.get("meta", {})
    off = timedelta(seconds=meta.get("gmtoffset", 9 * 3600))
    day = lambda ts: (datetime.fromtimestamp(ts, tz=timezone.utc) + off).date().isoformat()
    out: list[tuple[str, float]] = []
    for ts, c in zip(res.get("timestamp", []), closes):
        if c is None:
            continue
        d = day(ts)
        if out and out[-1][0] == d:
            out[-1] = (d, c * k)
        else:
            out.append((d, c * k))
    # Yahoo는 마지막 날 종가를 막대 대신 meta에만 넣는 경우가 있어 보충
    if meta.get("regularMarketPrice") and meta.get("regularMarketTime"):
        d, v = day(meta["regularMarketTime"]), meta["regularMarketPrice"] * k
        if out and out[-1][0] == d:
            out[-1] = (d, v)
        elif not out or out[-1][0] < d:
            out.append((d, v))
    return out


def _thin(s: list, n: int) -> list:
    """최대 n개 점으로 솎는다. 마지막 점은 항상 남긴다."""
    if len(s) <= n:
        return s
    step = len(s) / n
    idx = sorted({len(s) - 1 - int(i * step) for i in range(n)})
    return [s[i] for i in idx]


def _pct(a: float, b: float) -> float:
    return round((a / b - 1) * 100, 2)


def _close_on(s: list[tuple[str, float]], d: date) -> float | None:
    """d 당일 또는 그 이전 마지막 종가."""
    base = [v for x, v in s if x <= d.isoformat()]
    return base[-1] if base else None


def _quarters(s: list[tuple[str, float]], last_d: date) -> list[dict]:
    """진행 중인 분기를 포함한 최근 QUARTERS개 분기 각각의 시작 시점(직전 분기 말 종가) 대비 현재 종가 등락률."""
    y, q = last_d.year, (last_d.month - 1) // 3 + 1
    out = []
    for _ in range(QUARTERS):
        start = date(y, 3 * q - 2, 1) - timedelta(days=1)                 # 직전 분기 마지막 날
        end = date(y + (q == 4), (3 * q) % 12 + 1, 1) - timedelta(days=1)  # 이 분기 마지막 날
        a = _close_on(s, start)
        ok = a is not None and s[0][0] <= start.isoformat()
        out.append({"label": f"{y % 100}.{q}Q", "pct": _pct(s[-1][1], a) if ok else None, "ongoing": end > last_d})
        y, q = (y, q - 1) if q > 1 else (y - 1, 4)
    return out[::-1]


def _summarize(s: list[tuple[str, float]], points: int, decimals: int) -> dict:
    (d, last), (_, prev) = s[-1], s[-2]
    last_d = date.fromisoformat(d)
    year_ago = (last_d - timedelta(days=365)).isoformat()
    recent = [p for p in s if p[0] >= year_ago] or s        # 그래프·1년 수익률은 최근 1년
    out = {
        "date": d,
        "price": round(last, decimals),
        "change": round(last - prev, decimals),
        "change_pct": _pct(last, prev),
        "y1_pct": _pct(last, (_close_on(s, date.fromisoformat(year_ago)) or recent[0][1])),
    }
    for key, _, days in PERIOD_RETURNS:
        base = _close_on(s, last_d - timedelta(days=days))
        out[f"{key}_pct"] = _pct(last, base) if base else None
    out["quarters"] = _quarters(s, last_d)
    out["spark"] = [[x, round(v, decimals)] for x, v in _thin(recent, points)]
    return out


def _index(name: str, symbol: str, group: str, dec: int) -> dict | None:
    try:
        s = _series(symbol)
    except Exception as e:
        print(f"[market] {name}({symbol}) 실패: {e}")
        return None
    if len(s) < 2:
        return None
    return {"name": name, "symbol": symbol, "group": group, "decimals": dec, **_summarize(s, INDEX_POINTS, 2)}


_CAP = re.compile(r"(?:([\d,]+)조)?\s*(?:([\d,]+)억)?")


def _cap_eok(text: str) -> int | None:
    """'1,049조 4,070억' → 10494070 (억 원 단위)."""
    m = _CAP.fullmatch((text or "").strip())
    if not m or not any(m.groups()):
        return None
    jo, eok = (int(g.replace(",", "")) if g else 0 for g in m.groups())
    return jo * 10000 + eok


def _naver(code: str) -> dict:
    info: dict = {}
    try:
        b = requests.get(NAVER.format(code=code, kind="basic"), headers=UA, timeout=15).json()
        info["name"] = b.get("stockName")
        info["exch"] = (b.get("stockExchangeType") or {}).get("code")   # KS / KQ
        it = requests.get(NAVER.format(code=code, kind="integration"), headers=UA, timeout=15).json()
        total = {x.get("code"): x.get("value") for x in it.get("totalInfos", [])}
        info["cap"] = _cap_eok(total.get("marketValue"))
    except Exception as e:
        print(f"[market] 네이버 {code} 실패: {e}")
    return info


def _stock(name: str, code: str) -> dict | None:
    nv = _naver(code)
    exchs = [nv["exch"]] if nv.get("exch") in ("KS", "KQ") else ["KS", "KQ"]
    for ex in exchs:
        try:
            s = _series(f"{code}.{ex}")
        except Exception:
            continue
        if len(s) >= 2:
            return {"name": nv.get("name") or name, "code": code, "market": "코스피" if ex == "KS" else "코스닥",
                    "cap": nv.get("cap"), **_summarize(s, STOCK_POINTS, 0)}
    print(f"[market] {name}({code}) 시세 없음")
    return None


def fetch_market() -> dict:
    with ThreadPoolExecutor(max_workers=8) as pool:
        indices = [q for q in pool.map(lambda a: _index(*a), INDICES) if q]
        codes = {code: name for items in STOCK_GROUPS.values() for name, code in items}
        quotes = dict(zip(codes, pool.map(lambda c: _stock(codes[c], c), codes)))
    groups = []
    for gname, items in STOCK_GROUPS.items():
        pool_codes = codes if gname == ALL_GROUP else [c for _, c in items]
        qs = [quotes[c] for c in pool_codes if quotes.get(c)]
        # 시가총액 큰 순 (시총을 못 받은 종목은 config 순서대로 뒤에)
        qs = sorted(qs, key=lambda q: -(q["cap"] or 0))[:TOP_N]
        groups.append({"name": gname, "stocks": qs})
    print(f"[market] 지수 {len(indices)}개, 종목 {sum(1 for q in quotes.values() if q)}/{len(codes)}개")
    return {"indices": indices, "groups": groups}


def _fmt_pct(v) -> str:
    return "-" if v is None else f"{v:+.2f}%"


def market_text(m: dict) -> str:
    """Gemini 프롬프트에 넣을 시세 요약."""
    lines = [f"- {q['name']}: {q['price']:,.2f} (전일 대비 {q['change_pct']:+.2f}%, 1개월 {_fmt_pct(q.get('m1_pct'))}, "
             f"분기 시작 대비 " + " ".join(f"{x['label']}{'(진행 중)' if x['ongoing'] else ''} {_fmt_pct(x['pct'])}" for x in q.get('quarters', []))
             + f", 1년 {_fmt_pct(q.get('y1_pct'))}, 기준일 {q['date']})"
             for q in m.get("indices", [])]
    seen = set()
    for g in m.get("groups", []):
        for q in g["stocks"]:
            if q["code"] in seen:
                continue
            seen.add(q["code"])
            lines.append(f"- [{g['name']}] {q['name']}: {q['price']:,.0f}원 (전일 대비 {q['change_pct']:+.2f}%, 1개월 {_fmt_pct(q.get('m1_pct'))})")
    return "\n".join(lines)
