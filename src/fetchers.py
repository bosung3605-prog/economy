import requests
import feedparser
import yfinance as yf
import io
import csv

NASDAQ_TICKER = "^IXIC"
USD_KRW_TICKER = "USDKRW=X"
KOSPI_TICKER = "^KS11"
FRED_FEDFUNDS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS"

NEWS_FEEDS = [
    ("한국경제", "https://www.hankyung.com/feed/economy"),
    ("매일경제", "https://www.mk.co.kr/rss/30100041/"),
    ("연합뉴스 경제", "https://www.yna.co.kr/economy/rss.xml"),
]

FALLBACK_FEEDS = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
]

PRIORITY_KEYWORDS = [
    "코스피", "원달러", "환율", "한국은행", "기준금리", "수출", "수입", "무역",
    "반도체", "삼성", "현대", "sk", "lg", "포스코", "gdp", "성장률",
    "인플레이션", "물가", "소비자물가", "고용", "실업", "부동산", "금리",
    "달러", "외환", "경상수지", "재정", "세금", "예산",
    "fed", "federal reserve", "rate", "interest", "nasdaq", "dollar",
    "inflation", "recession", "jobs", "cpi", "tariff", "trade",
    "powell", "fomc", "treasury", "earnings",
]

# Yahoo Finance는 클라우드 IP의 기본 요청을 차단 — 브라우저 User-Agent로 우회
_YF_SESSION = requests.Session()
_YF_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
})


def _score_news(title: str, summary: str) -> int:
    text = (title + " " + summary).lower()
    return sum(1 for kw in PRIORITY_KEYWORDS if kw in text)


def _fetch_ticker(ticker: str, period: str = "7d") -> dict | None:
    try:
        t = yf.Ticker(ticker, session=_YF_SESSION)
        hist = t.history(period=period)
        if len(hist) < 2:
            print(f"[경고] {ticker}: 데이터 부족 ({len(hist)}행)")
            return None
        today_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        change = today_close - prev_close
        change_pct = (change / prev_close) * 100
        print(f"[OK] {ticker}: {today_close:.2f} (전일比 {change:+.2f})")
        return {
            "value": round(today_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "date": hist.index[-1].strftime("%Y-%m-%d"),
        }
    except Exception as e:
        print(f"[오류] {ticker} 수집 실패: {e}")
        return None


def fetch_market_data() -> dict:
    return {
        "nasdaq": _fetch_ticker(NASDAQ_TICKER),
        "usdkrw": _fetch_ticker(USD_KRW_TICKER),
        "kospi": _fetch_ticker(KOSPI_TICKER),
    }


def fetch_interest_rate() -> dict | None:
    try:
        resp = requests.get(FRED_FEDFUNDS_URL, timeout=15)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = [r for r in reader if r.get("FEDFUNDS") not in ("", ".")]
        if not rows:
            print("[경고] FRED: 데이터 없음")
            return None
        latest = rows[-1]
        value = float(latest["FEDFUNDS"])
        print(f"[OK] FRED 기준금리: {value}% ({latest['DATE']})")
        return {"value": value, "date": latest["DATE"]}
    except Exception as e:
        print(f"[오류] FRED 기준금리 수집 실패: {e}")
        return None


def _parse_feed(source_name: str, url: str) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            published = entry.get("published", "")
            score = _score_news(title, summary)
            items.append({
                "source": source_name,
                "title": title,
                "summary": summary[:200],
                "link": link,
                "published": published,
                "score": score,
            })
        print(f"[OK] {source_name}: {len(items)}건")
    except Exception as e:
        print(f"[오류] {source_name} 피드 수집 실패: {e}")
    return items


def fetch_news(max_items: int = 8) -> list[dict]:
    items = []
    for source_name, url in NEWS_FEEDS:
        items.extend(_parse_feed(source_name, url))

    if not items:
        print("[경고] 한국 뉴스 피드 전체 실패 — fallback 피드 사용")
        for source_name, url in FALLBACK_FEEDS:
            items.extend(_parse_feed(source_name, url))

    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:max_items]
