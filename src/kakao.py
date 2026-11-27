"""카카오톡 '나에게 보내기'로 브리핑 링크를 보낸다."""
import json
import os
from datetime import date

import requests

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TEXT_LIMIT = 200  # 텍스트 템플릿 최대 글자 수


def refresh_access_token() -> str:
    """refresh token으로 access token을 새로 받는다.
    refresh token이 갱신되어 돌아오면 NEW_REFRESH_TOKEN_FILE에 저장해 워크플로가 Secret을 업데이트하게 한다."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.environ["KAKAO_REST_API_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
    }
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        payload["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    resp = requests.post(TOKEN_URL, data=payload, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"카카오 토큰 갱신 실패 {resp.status_code}: {resp.text}")
    tok = resp.json()

    new_refresh = tok.get("refresh_token")
    out = os.environ.get("NEW_REFRESH_TOKEN_FILE")
    if new_refresh and out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(new_refresh)
        print("[kakao] refresh token이 갱신되었습니다 (Secret 업데이트 예정)")
    return tok["access_token"]


def _send(access_token: str, template: dict) -> None:
    resp = requests.post(
        MEMO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=20,
    )
    if resp.status_code != 200 or resp.json().get("result_code") != 0:
        raise RuntimeError(f"카카오 메시지 전송 실패 {resp.status_code}: {resp.text}")


def _text_template(text: str, url: str) -> dict:
    if len(text) > TEXT_LIMIT:
        text = text[: TEXT_LIMIT - 1] + "…"
    return {
        "object_type": "text",
        "text": text,
        "link": {"web_url": url, "mobile_web_url": url},
        "button_title": "대시보드 열기",
    }


KAKAO_NUMBERS = ["^KS11", "KRW=X", "^GSPC"]   # 카톡에 숫자로 보여줄 지표 (코스피, 원/달러, S&P 500)


def _numbers(data: dict) -> str:
    idx = {q["symbol"]: q for q in (data.get("market") or {}).get("indices", [])}
    parts = []
    for sym in KAKAO_NUMBERS:
        q = idx.get(sym)
        if q:
            arrow = "▲" if q["change"] > 0 else "▼" if q["change"] < 0 else "-"
            parts.append(f"{q['name']} {q['price']:,.2f} {arrow}{abs(q['change_pct']):.2f}%")
    return " · ".join(parts)


def build_message(data: dict, d: date) -> str:
    """제목 + 핵심 숫자 한 줄 + 증시 한 줄 요약 (200자 넘으면 _text_template에서 자름)."""
    lines = [f"{d.month}/{d.day} 국내 뉴스 · 증시 브리핑"]
    nums = _numbers(data)
    if nums:
        closed = (data.get("market") or {}).get("closed")
        lines.append(("(새 거래 없음) " if closed == "all" else "") + nums)
    if data.get("market_headline") and (data.get("market") or {}).get("closed") != "all":
        lines.append(data["market_headline"])
    return "\n".join(lines)


def notify_failure(d: date, run_url: str) -> None:
    """빌드가 실패했을 때 알림 (버튼은 Actions 실행 로그로 연결)."""
    token = refresh_access_token()
    _send(token, {
        "object_type": "text",
        "text": f"{d.month}/{d.day} 국내 브리핑 생성에 실패했습니다. 오늘 대시보드는 갱신되지 않았습니다.",
        "link": {"web_url": run_url, "mobile_web_url": run_url},
        "button_title": "실행 로그 보기",
    })
    print("[kakao] 실패 알림 전송")


def notify(data: dict, d: date, dashboard_url: str) -> None:
    token = refresh_access_token()
    _send(token, _text_template(build_message(data, d), dashboard_url))
    print("[kakao] 전송 완료")
