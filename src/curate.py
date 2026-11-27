"""Gemini(무료 등급)로 국내 이슈를 고르고 요약한 뒤, 보도 언론사 수를 더한 점수로 TOP 10을 정한다.
같은 호출에서 시세 숫자를 바탕으로 한 시황 코멘트도 받는다."""
import json
import os
import time

import requests

from .config import (CANDIDATE_ISSUES, CATEGORIES, COVERAGE_CAP, COVERAGE_WEIGHT,
                     FEEDS, MODELS, OUTLET_ALIASES, TRUSTED_OUTLETS)

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """당신은 경제에 밝은 국내 뉴스 에디터입니다.
아래는 국내 언론의 최근 24시간 기사 후보 목록과 최근 시세입니다. 한국에서 가장 중요한 이슈 {k}개를 고르세요.

선정 기준:
- 국내 정치·경제·산업·사회에 미치는 영향의 크기를 최우선으로 봅니다. 경제·증시에 영향이 큰 뉴스를 조금 더 무겁게 봅니다.
- 여러 언론이 함께 다룬 사건일수록 중요도가 높을 가능성이 큽니다. 같은 사건을 다룬 후보들은 하나의 이슈로 묶고, 묶인 후보 번호를 모두 source_ids에 넣습니다.
  단, 같은 구체적 사건만 묶고 넓은 주제(예: '정부 정책 전반')로 여러 사건을 한데 묶지 마세요.
- 연예·스포츠 단신, 사건사고 단신, 생활 정보, 의견 칼럼은 정말 큰 사건이 아니면 제외합니다.

작성 규칙 (모두 한국어, 자연스러운 뉴스 문체):
- rank: 1이 가장 중요. 1~{k} 중복 없이.
- category: 다음 중 하나: {categories}
- title: 30자 안팎의 기사 제목
- summary: 핵심 사실 2~3문장. 후보 목록에 있는 정보만 사용하고, 없는 수치나 사실을 지어내지 마세요.
- why_it_matters: 이 뉴스가 왜 중요한지, 생활·경제·투자에 주는 의미 한 문장
- related: 이 뉴스와 직접 관련된 업종이나 상장 종목 이름 0~3개 (예: ["반도체", "삼성전자"]). 관련이 뚜렷하지 않으면 빈 배열.
- headline_of_day: 오늘 국내 뉴스(정치·경제·사회 전반) 흐름을 한 문장으로 요약. 증시 이야기는 되도록 빼고 market_headline에 씁니다.
- market_headline: 오늘 증시 흐름을 한 문장으로 요약 (코스피·해외 증시·환율, 눈에 띄는 국내 업종·종목). 숫자는 아래 시세에 있는 것만 씁니다.
- market_comment: 아래 시세 숫자와 기사 후보를 바탕으로 한 시황 2~3문장. 전일 움직임을 중심으로, 필요하면 1개월·분기 흐름과 해외 증시를 곁들입니다. 숫자는 아래 시세에 있는 것만 쓰고, 원인은 기사에 근거가 있을 때만 언급합니다. 투자 권유 표현은 쓰지 않습니다.

아래 형식의 JSON만 출력하세요:
{{"headline_of_day": "...", "market_headline": "...", "market_comment": "...", "stories": [{{"rank": 1, "category": "...", "title": "...", "summary": "...", "why_it_matters": "...", "related": ["..."], "source_ids": [0, 5]}}]}}

오늘 날짜(KST): {date}

최근 시세:
{market}

기사 후보 {n}건:
{candidates}
"""

REQUIRED = ["rank", "category", "title", "summary", "why_it_matters", "source_ids"]


def _outlet(it: dict) -> str:
    name = it.get("outlet") or it["source"]
    return OUTLET_ALIASES.get(name, name)


COUNTED_OUTLETS = TRUSTED_OUTLETS | {OUTLET_ALIASES.get(n, n) for n, _ in FEEDS if not n.startswith("Google News")}


def _score(stories: list[dict]) -> list[dict]:
    """중요도(Gemini 순위 0~1) × (1-W) + 보도량((언론사 수-1)/(CAP-1)) × W 로 다시 정렬."""
    n = len(stories)
    for i, s in enumerate(stories):
        outlets = len({src["name"] for src in s["sources"] if src["name"] in COUNTED_OUTLETS})
        importance = 1.0 if n == 1 else (n - 1 - i) / (n - 1)
        coverage = (min(max(outlets, 1), COVERAGE_CAP) - 1) / (COVERAGE_CAP - 1)
        s["llm_rank"] = i + 1
        s["outlets"] = outlets
        s["score"] = round((1 - COVERAGE_WEIGHT) * importance + COVERAGE_WEIGHT * coverage, 3)
    return sorted(stories, key=lambda s: (-s["score"], s["llm_rank"]))


def _format_candidates(items: list[dict]) -> str:
    lines = []
    for it in items:
        line = f"[{it['id']}] ({_outlet(it)}) {it['title']}"
        if it["summary"]:
            line += f" — {it['summary']}"
        lines.append(line)
    return "\n".join(lines)


class Busy(Exception):
    """일시적 혼잡(429/5xx) — 나중에 다시 시도할 가치가 있음."""


def _call(model: str, prompt: str) -> dict:
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
    }
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    try:
        r = requests.post(API.format(model=model), headers=headers, json=body, timeout=300)
    except requests.RequestException as e:
        raise Busy(str(e))
    if r.status_code == 200:
        data = r.json()
        text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        print(f"[curate] {model} 사용, tokens={data.get('usageMetadata', {})}")
        return json.loads(text)
    if r.status_code in (429, 500, 502, 503, 504):
        raise Busy(f"{r.status_code}")
    raise RuntimeError(f"오류 {r.status_code}: {r.text[:300]}")


def _validate(data: dict) -> None:
    stories = data.get("stories")
    if not isinstance(stories, list) or len(stories) < 5:
        raise ValueError(f"stories가 부족합니다: {stories!r:.200}")
    for s in stories:
        missing = [k for k in REQUIRED if k not in s]
        if missing:
            raise ValueError(f"필드 누락 {missing}: {s!r:.200}")
        if s["category"] not in CATEGORIES:
            s["category"] = "기타"
        if not isinstance(s.get("related"), list):
            s["related"] = []


def generate(prompt: str, validate, rounds: int = 8, tag: str = "curate") -> dict:
    """모델을 번갈아 가며 호출. 무료 등급 혼잡(503) 시 rounds번까지 기다렸다 재시도 (8회면 최대 약 20분)."""
    models = list(MODELS)
    errors: list[str] = []
    for rnd in range(rounds):
        for model in list(models):
            try:
                data = _call(model, prompt)
                validate(data)
                return data
            except Busy as e:
                print(f"[{tag}] {model} 혼잡({e})")
            except Exception as e:
                print(f"[{tag}] {model} 실패: {e}")
                errors.append(f"{model}: {e}")
                models.remove(model)
        if not models or rnd == rounds - 1:
            break
        wait = min(30 * (rnd + 1), 240)
        print(f"[{tag}] 모든 모델 혼잡, {wait}초 후 다시 시도 ({rnd + 1}/{rounds})")
        time.sleep(wait)
    raise RuntimeError("Gemini 호출 실패 (혼잡 또는 오류):\n" + "\n".join(errors))


def attach_sources(stories: list[dict], items: list[dict]) -> list[dict]:
    by_id = {it["id"]: it for it in items}
    for s in stories:
        s["sources"] = [
            {"name": _outlet(by_id[sid]), "title": by_id[sid]["title"], "link": by_id[sid]["link"]}
            for sid in dict.fromkeys(s.pop("source_ids")) if isinstance(sid, int) and sid in by_id
        ]
    return stories


def curate(items: list[dict], date_label: str, market: str) -> dict:
    prompt = PROMPT.format(
        k=CANDIDATE_ISSUES, categories=", ".join(CATEGORIES), date=date_label,
        market=market or "(시세 없음)", n=len(items), candidates=_format_candidates(items),
    )
    data = generate(prompt, _validate)
    stories = attach_sources(sorted(data["stories"], key=lambda s: s["rank"]), items)
    stories = _score(stories)[:10]
    for i, s in enumerate(stories, start=1):
        s["rank"] = i
        print(f"[curate] {i}위 (Gemini {s['llm_rank']}위, 언론사 {s['outlets']}곳, 점수 {s['score']}) {s['title']}")
    return {
        "headline_of_day": data.get("headline_of_day", ""),
        "market_headline": data.get("market_headline", ""),
        "market_comment": data.get("market_comment", ""),
        "stories": stories,
    }
