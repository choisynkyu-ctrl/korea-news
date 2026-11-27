"""보유 종목 평가손익 · 수익률 · 배당금.

대시보드와 저장소가 공개라 수량·평단가는 저장소에 두지 않는다.
- 입력: GitHub Secret HOLDINGS_JSON  예) [{"code":"360750","qty":1241,"avg":17852}, ...]
- 계산 결과는 HOLDINGS_PASSWORD로 암호화(PBKDF2-SHA256 → AES-256-GCM)해 JSON에 넣고,
  페이지에서 비밀번호를 넣어야 브라우저 안에서 풀린다 (서버·저장소에는 평문이 남지 않음).
두 Secret 중 하나라도 없으면 이 기능은 조용히 빠진다.
"""
import base64
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone

import requests

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = {"User-Agent": "Mozilla/5.0 (daily-korea-briefing)"}
ITER = 200_000
DIV_TAX = 0.154          # 배당소득세 15.4% (지방세 포함)


def load() -> list[dict]:
    raw = os.environ.get("HOLDINGS_JSON", "").strip()
    if not raw:
        return []
    try:
        return [{"code": str(h["code"]), "qty": float(h["qty"]), "avg": float(h["avg"])} for h in json.loads(raw)]
    except Exception as e:
        print(f"[holdings] HOLDINGS_JSON 형식 오류: {e}")
        return []


def _dividends(code: str, market: str) -> list[tuple[str, float]]:
    """최근 2년 분배금 [(지급 기준일 YYYY-MM-DD, 1주당 금액), ...] 오래된 순."""
    sym = f"{code}.{'KQ' if market == '코스닥' else 'KS'}"
    try:
        r = requests.get(CHART.format(symbol=sym), params={"range": "2y", "interval": "1d", "events": "div"},
                         headers=UA, timeout=20)
        ev = (r.json()["chart"]["result"][0].get("events") or {}).get("dividends", {})
    except Exception as e:
        print(f"[holdings] {code} 분배금 조회 실패: {e}")
        return []
    kst = timezone(timedelta(hours=9))
    return sorted((datetime.fromtimestamp(v["date"], tz=kst).date().isoformat(), float(v["amount"])) for v in ev.values())


def compute(holdings: list[dict], market: dict, today: date) -> dict | None:
    quotes = {q["code"]: q for g in market.get("groups", []) for q in g["stocks"]}
    rows = []
    for h in holdings:
        q = quotes.get(h["code"])
        if not q:
            print(f"[holdings] {h['code']} 시세 없음 → 제외")
            continue
        qty, avg, px = h["qty"], h["avg"], q["price"]
        divs = _dividends(h["code"], q.get("market", ""))
        cut = (today - timedelta(days=365)).isoformat()
        last12 = [(d, a) for d, a in divs if d > cut]
        per_share = sum(a for _, a in last12)
        rows.append({
            "name": q["name"], "code": h["code"], "qty": qty, "avg": avg, "price": px,
            "value": px * qty, "cost": avg * qty, "pnl": (px - avg) * qty,
            "ret": (px / avg - 1) * 100, "day": q["change"] * qty, "day_pct": q["change_pct"],
            "div_year": per_share * qty, "div_count": len(last12),
            "div_last": ({"date": last12[-1][0], "amount": last12[-1][1], "total": last12[-1][1] * qty} if last12 else None),
            "div_yield": per_share / px * 100 if px else 0,      # 현재가 기준 분배율
            "div_yoc": per_share / avg * 100 if avg else 0,      # 매수가 기준 분배율
        })
    if not rows:
        return None
    tot = {k: sum(r[k] for r in rows) for k in ("value", "cost", "pnl", "day", "div_year")}
    tot["ret"] = (tot["value"] / tot["cost"] - 1) * 100 if tot["cost"] else 0
    tot["day_pct"] = tot["day"] / (tot["value"] - tot["day"]) * 100 if tot["value"] != tot["day"] else 0
    tot["div_after_tax"] = tot["div_year"] * (1 - DIV_TAX)
    return {"date": market.get("kr_date") or today.isoformat(), "rows": rows, "total": tot}


def _key(password: str, salt: bytes, iterations: int = ITER) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)


def encrypt(payload: dict, password: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(password, salt)).encrypt(iv, json.dumps(payload, ensure_ascii=False).encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "iter": ITER, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def decrypt(enc: dict, password: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    d = lambda k: base64.b64decode(enc[k])
    pt = AESGCM(_key(password, d("salt"), enc["iter"])).decrypt(d("iv"), d("ct"), None)
    return json.loads(pt)


def build(market: dict, today: date) -> dict | None:
    """market을 받아 암호화된 보유 수익 블록을 돌려준다 (Secret이 없으면 None)."""
    holdings, pw = load(), os.environ.get("HOLDINGS_PASSWORD", "")
    if not holdings or not pw:
        if holdings or pw:
            print("[holdings] HOLDINGS_JSON과 HOLDINGS_PASSWORD가 둘 다 있어야 합니다 → 건너뜀")
        return None
    p = compute(holdings, market, today)
    if not p:
        return None
    print(f"[holdings] {len(p['rows'])}종목 계산 완료 (암호화해 저장)")
    return encrypt(p, pw)
