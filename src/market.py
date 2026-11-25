"""지수·환율·관심 종목 시세를 모은다 (Yahoo Finance 공개 차트 API)."""
from datetime import datetime, timedelta, timezone

import requests

from .config import INDICES, SCALE, SPARK_RANGE, WATCHLIST

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (daily-korea-briefing)"


def _series(symbol: str) -> list[tuple[str, float]]:
    """[(YYYY-MM-DD, 종가), ...] 오래된 순. 장중·휴장으로 비어 있는 값(None)은 뺀다."""
    r = requests.get(CHART.format(symbol=symbol), params={"range": SPARK_RANGE, "interval": "1d"},
                     headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    closes = res["indicators"]["quote"][0]["close"]
    k = SCALE.get(symbol, 1)
    meta = res.get("meta", {})
    # 날짜는 거래소 현지 기준 (미국 지수의 11/25 장은 한국 시간으로 11/26 새벽에 끝나도 11/25)
    off = timedelta(seconds=meta.get("gmtoffset", 9 * 3600))
    day = lambda ts: (datetime.fromtimestamp(ts, tz=timezone.utc) + off).date().isoformat()
    out = []
    for ts, c in zip(res.get("timestamp", []), closes):
        if c is None:
            continue
        d = day(ts)
        if out and out[-1][0] == d:   # 같은 날 막대가 두 번 오면 마지막 값
            out[-1] = (d, c * k)
        else:
            out.append((d, c * k))
    # Yahoo는 마지막 날 막대의 종가를 비워 두고 meta에만 넣는 경우가 있어 보충한다
    if meta.get("regularMarketPrice") and meta.get("regularMarketTime"):
        d = day(meta["regularMarketTime"])
        v = meta["regularMarketPrice"] * k
        if out and out[-1][0] == d:
            out[-1] = (d, v)
        elif not out or out[-1][0] < d:
            out.append((d, v))
    return out


def _quote(name: str, symbol: str, **extra) -> dict | None:
    try:
        s = _series(symbol)
    except Exception as e:  # 한 종목이 실패해도 계속
        print(f"[market] {name}({symbol}) 실패: {e}")
        return None
    if len(s) < 2:
        print(f"[market] {name}({symbol}) 데이터 부족")
        return None
    (d, last), (_, prev) = s[-1], s[-2]
    first = s[0][1]
    return {
        "name": name, "symbol": symbol, **extra,
        "date": d,
        "price": round(last, 4),
        "change": round(last - prev, 4),
        "change_pct": round((last / prev - 1) * 100, 2),
        "period_pct": round((last / first - 1) * 100, 2),
        "spark": [[x, round(v, 4)] for x, v in s],
    }


def fetch_market() -> dict:
    indices = [q for n, sym, grp, dec in INDICES if (q := _quote(n, sym, group=grp, decimals=dec))]
    stocks = [q for n, sym in WATCHLIST if (q := _quote(n, sym, code=sym.split(".")[0]))]
    print(f"[market] 지수 {len(indices)}개, 종목 {len(stocks)}개")
    return {"indices": indices, "stocks": stocks}


def market_text(m: dict) -> str:
    """Gemini 프롬프트에 넣을 시세 요약."""
    lines = [f"- {q['name']}: {q['price']:,.2f} (전일 대비 {q['change_pct']:+.2f}%, 1개월 {q['period_pct']:+.2f}%, 기준일 {q['date']})"
             for q in m.get("indices", [])]
    lines += [f"- {q['name']}: {q['price']:,.0f}원 ({q['change_pct']:+.2f}%)" for q in m.get("stocks", [])]
    return "\n".join(lines)
