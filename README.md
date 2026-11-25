# 🇰🇷 매일 아침 국내 뉴스 · 증시 브리핑

매일 오전 7시 무렵, 국내 주요 언론 RSS(연합뉴스 종합/경제/마켓 · 한겨레 · 경향 · 동아 · 조선 · 매일경제 · SBS · JTBC · Google News 종합/경제)에서
최근 30시간 기사를 모으고, **Yahoo Finance**에서 지수·환율·관심 종목 시세(최근 1개월)를 받아
**Google Gemini(무료 등급)** 가 중요 이슈 15개 선정·요약 + 시황 코멘트를 쓴 뒤,
**Gemini 중요도 60% + 보도한 언론사 수 40%** 점수로 TOP 10을 정합니다.
결과는 **GitHub Pages 대시보드**에 올라가고, **카카오톡 '나와의 채팅'** 으로 대시보드 링크가 옵니다.

> `News Scrap (World)` 와 같은 구조입니다. 다른 점: 국내 RSS, `src/market.py`(시세), 시황 코멘트, 뉴스별 관련 업종·종목 태그, 대시보드 레이아웃.

```
GitHub Actions (06:20 KST, 간밤 미국 장 마감 후)
  ├─ RSS 수집 (src/collect.py)
  ├─ 시세 수집 (src/market.py)           → 코스피·코스닥·환율·미국 지수·유가·관심 종목
  ├─ Gemini 선정·요약·시황 (src/curate.py) → docs/data/YYYY-MM-DD.json
  ├─ 주간·월간 흐름 (src/digest.py)
  ├─ 대시보드 생성 (src/render.py)        → docs/index.html, docs/archive/
  ├─ git push → GitHub Pages 반영
  └─ 카카오톡 전송 (src/kakao.py)
```

## 대시보드 구성
1. **헤더**: 일간 한 줄 요약 · 주간 · 월간 흐름 (2일/8일치 이상 쌓이면 표시), 지난 날짜 바로가기
2. **시장**: 코스피 · 코스닥 · 원/달러 · 원/엔 · S&P 500 · 나스닥 · 필라델피아 반도체 · WTI
   — 종가, 전일 대비(▲빨강/▼파랑), 1개월 추이 그래프(마우스를 올리면 날짜·값), Gemini 시황 코멘트
3. **관심 종목**: 종가 · 전일 대비 · 1개월 수익률 · 추이 (머리글 클릭 시 정렬)
4. **주요 뉴스 TOP 10**: 분야 필터, 요약 · 왜 중요한가 · 관련 업종/종목 태그 · 원문 링크

## 처음 설정 (World와 동일)
1. GitHub에 새 공개 저장소(예: `korea-news`)를 만들고 이 폴더를 push
2. Settings → Pages → Branch `main` / 폴더 `/docs`
3. Secret 등록 (World에서 쓴 Gemini 키·카카오 앱을 그대로 써도 됩니다):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\setup_secrets.ps1
   ```
4. 카카오 앱 → 플랫폼 → Web 사이트 도메인에 `https://<GitHub아이디>.github.io` 가 있는지 확인
5. Actions → **Daily Korea Briefing** → Run workflow 로 첫 실행

## 로컬 미리보기 (API 키 없이)
실제 시세와 RSS 헤드라인으로 화면만 그려 봅니다 (Gemini 요약 자리는 안내 문구):
```powershell
python -m src.main preview preview
```

## 수정 포인트 (`src/config.py`)
- 관심 종목: `WATCHLIST` (Yahoo 심볼: 코스피 `005930.KS`, 코스닥 `196170.KQ`)
- 지수·환율: `INDICES`
- 뉴스 소스: `FEEDS`, 보도량에 세는 언론사: `TRUSTED_OUTLETS`
- 분야: `CATEGORIES` (색은 `src/render.py`의 `CAT_COLORS`)
- 선정 기준·시황 문체: `src/curate.py`의 `PROMPT`

## 참고
- 시세는 Yahoo Finance 비공식 공개 API의 일별 종가입니다. 막히거나 값이 비면 그 종목만 빠지고 나머지는 계속 만듭니다.
- 한국경제 RSS는 자동 접속을 막아(403) Google News를 통해서만 들어옵니다.
- 대시보드는 정보 정리용이며 투자 권유가 아닙니다.
