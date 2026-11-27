"""사용법:
  python -m src.main build     # 뉴스 수집 + 시세 → Gemini 선정/요약 → docs/ 대시보드 생성
  python -m src.main notify    # docs/data/latest.json 날짜 확인 후 카카오톡 전송
  python -m src.main render    # 저장된 JSON으로 HTML만 다시 생성 (API 호출 없음)
  python -m src.main preview <폴더>  # Gemini 없이 실제 시세 + RSS 헤드라인으로 화면 미리보기 (docs/는 건드리지 않음)
"""
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from .config import DATA_DIR, KST


def today_kst() -> date:
    return datetime.now(KST).date()


def cmd_build() -> None:
    from .collect import collect
    from .curate import curate
    from .digest import digest
    from .market import fetch_market, mark_closed, market_text
    from .render import save_and_render

    d = today_kst()
    items = collect()
    if len(items) < 20:
        raise SystemExit(f"후보 기사가 너무 적습니다 ({len(items)}건). RSS 소스를 확인하세요.")
    market = fetch_market()
    mark_closed(market, d)
    note = {"all": "(주말·휴일로 어제 새 거래가 없었습니다. 아래는 직전 거래일 종가입니다.)\n",
            "kr": "(국내 증시 휴장: 코스피는 직전 거래일 종가입니다.)\n"}.get(market["closed"], "")
    data = curate(items, d.isoformat(), note + market_text(market))
    if market["closed"] == "all":
        kr = market.get("kr_date") or ""
        data["market_comment"] = ""
        data["market_headline"] = f"주말·휴일로 새 거래가 없습니다. 시장 숫자는 {int(kr[5:7])}/{int(kr[8:])} 종가 기준입니다." if kr else ""
    data["market"] = market
    data["digest"] = digest(data, d)
    save_and_render(data, d)


def cmd_notify() -> None:
    from .kakao import notify

    data = json.loads((DATA_DIR / "latest.json").read_text(encoding="utf-8"))
    d = date.fromisoformat(data["date"])
    if d != today_kst():
        raise SystemExit(f"latest.json 날짜({d})가 오늘이 아닙니다. build가 실패했는지 확인하세요.")
    notify(data, d, os.environ["DASHBOARD_URL"])


def cmd_notify_fail() -> None:
    from .kakao import notify_failure
    notify_failure(today_kst(), os.environ.get("RUN_URL") or os.environ["DASHBOARD_URL"])


def cmd_render() -> None:
    from .render import render_all
    render_all()


def cmd_preview() -> None:
    """레이아웃 확인용. 뉴스 카드는 RSS 원문 제목·요약을 그대로 채우고 '미리보기'라고 표시한다."""
    from .collect import collect
    from .market import fetch_market
    from .render import render_page

    out = Path(sys.argv[2] if len(sys.argv) > 2 else "preview")
    out.mkdir(parents=True, exist_ok=True)
    d = today_kst()
    items = [it for it in collect() if not it["source"].startswith("Google")][:10]
    stories = [{
        "rank": i, "category": "기타", "title": it["title"],
        "summary": it["summary"] or "(RSS 요약 없음)",
        "why_it_matters": "미리보기: 실제 실행 때는 Gemini가 이 자리에 '왜 중요한가'를 씁니다.",
        "related": [], "outlets": 1,
        "sources": [{"name": it["outlet"], "title": it["title"], "link": it["link"]}],
    } for i, it in enumerate(items, start=1)]
    data = {
        "date": d.isoformat(),
        "headline_of_day": "미리보기 화면입니다. 실제 실행 때는 Gemini가 오늘의 국내 뉴스 흐름을 한 문장으로 씁니다.",
        "market_comment": "미리보기: 실제 실행 때는 아래 시세 숫자와 경제 기사를 바탕으로 한 시황 코멘트 2~3문장이 들어갑니다.",
        "stories": stories, "market": fetch_market(), "digest": {},
    }
    (out / "preview.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "index.html").write_text(render_page(data, d, "", [d]), encoding="utf-8")
    print(f"[preview] {out / 'index.html'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    {"build": cmd_build, "notify": cmd_notify, "notify-fail": cmd_notify_fail,
     "render": cmd_render, "preview": cmd_preview}[cmd]()
