"""설정값: 뉴스 소스, 시세 종목, 모델, 경로."""
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"              # GitHub Pages 루트
DATA_DIR = DOCS / "data"          # 날짜별 JSON
ARCHIVE_DIR = DOCS / "archive"    # 날짜별 HTML

# Gemini 무료 등급 모델. 앞에서부터 시도하고, 없어지거나 실패하면 다음 모델 사용
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-2.5-flash"]

# 최근 몇 시간 이내 기사만 후보로 사용
LOOKBACK_HOURS = 30
# 소스당 최대 후보 수
MAX_PER_FEED = 25

# 국내 주요 언론 RSS (공개 피드). 한국경제 RSS는 자동 접속을 막아(403) Google News로만 받는다.
FEEDS = [
    ("연합뉴스", "https://www.yna.co.kr/rss/news.xml"),
    ("연합뉴스 경제", "https://www.yna.co.kr/rss/economy.xml"),
    ("연합뉴스 마켓", "https://www.yna.co.kr/rss/market.xml"),
    ("한겨레", "https://www.hani.co.kr/rss/"),
    ("경향신문", "https://www.khan.co.kr/rss/rssdata/total_news.xml"),
    ("동아일보", "https://rss.donga.com/total.xml"),
    ("조선일보", "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("매일경제", "https://www.mk.co.kr/rss/30000001/"),
    ("SBS", "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01"),
    ("JTBC", "https://news-ex.jtbc.co.kr/v1/get/rss/section/10"),
    # Google News: 여러 매체 기사를 모은 피드. 원래 언론사가 TRUSTED_OUTLETS에 있으면 보도량에 센다
    ("Google News", "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"),
    ("Google News 경제", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"),
]

# 같은 언론사로 볼 이름들 (보도 건수는 언론사 단위로 센다)
OUTLET_ALIASES = {
    "연합뉴스 경제": "연합뉴스", "연합뉴스 마켓": "연합뉴스",
    "KBS 뉴스": "KBS", "MBC 뉴스": "MBC", "SBS 뉴스": "SBS", "YTN 뉴스": "YTN",
    "JTBC 뉴스": "JTBC", "한겨레신문": "한겨레", "중앙일보 | 중앙일보": "중앙일보",
    "매일경제 | 매일경제": "매일경제", "한국경제TV": "한국경제TV", "chosun.com": "조선일보",
}

# 보도량 점수에 세는 언론사. FEEDS로 직접 받는 언론사(Google News 제외)는 자동 포함되고,
# Google News로 들어온 기사는 아래 목록에 있는 언론사일 때만 센다.
TRUSTED_OUTLETS = {
    "KBS", "MBC", "YTN", "연합뉴스TV", "뉴스1", "뉴시스",
    "중앙일보", "한국일보", "국민일보", "세계일보", "서울신문",
    "한국경제", "서울경제", "머니투데이", "이데일리", "파이낸셜뉴스", "아시아경제", "헤럴드경제", "조선비즈",
}

# TOP 10 점수 = (1 - COVERAGE_WEIGHT) × Gemini 중요도 + COVERAGE_WEIGHT × 보도 언론사 수
CANDIDATE_ISSUES = 15
COVERAGE_WEIGHT = 0.4
COVERAGE_CAP = 6

CATEGORIES = ["정치", "경제/정책", "증시/금융", "산업/기업", "부동산", "사회", "IT/과학", "국제/외교", "기타"]

# ── 시세 (Yahoo Finance 공개 차트 API, 키 불필요) ─────────────────────────
# (표시 이름, Yahoo 심볼, 그룹, 소수 자리)
INDICES = [
    ("코스피", "^KS11", "국내 증시", 2),
    ("코스닥", "^KQ11", "국내 증시", 2),
    ("원/달러", "KRW=X", "환율", 2),
    ("원/엔(100엔)", "JPYKRW=X", "환율", 2),
    ("S&P 500", "^GSPC", "간밤 미국", 2),
    ("나스닥", "^IXIC", "간밤 미국", 2),
    ("필라델피아 반도체", "^SOX", "간밤 미국", 2),
    ("WTI 유가", "CL=F", "원자재", 2),
]
# 원/엔은 1엔 기준으로 오므로 100을 곱해 표시
SCALE = {"JPYKRW=X": 100}

# 관심 종목 (이름, Yahoo 심볼). 코스피 .KS / 코스닥 .KQ
WATCHLIST = [
    ("삼성전자", "005930.KS"),
    ("SK하이닉스", "000660.KS"),
    ("LG에너지솔루션", "373220.KS"),
    ("삼성바이오로직스", "207940.KS"),
    ("현대차", "005380.KS"),
    ("기아", "000270.KS"),
    ("셀트리온", "068270.KS"),
    ("KB금융", "105560.KS"),
    ("한화에어로스페이스", "012450.KS"),
    ("NAVER", "035420.KS"),
    ("카카오", "035720.KS"),
    ("알테오젠", "196170.KQ"),
]
SPARK_RANGE = "1mo"   # 추이 그래프 기간
