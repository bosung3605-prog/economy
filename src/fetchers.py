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

PRIORITY_KEYWORDS = [
    # 한국 경제
    "코스피", "원달러", "환율", "한국은행", "기준금리", "수출", "수입", "무역",
    "반도체", "삼성", "현대", "sk", "lg", "포스코", "gdp", "성장률",
    "인플레이션", "물가", "소비자물가", "고용", "실업", "부동산", "금리",
    "달러", "외환", "경상수지", "재정", "세금", "예산",
    # 미국·글로벌 (나스닥·금리 영향)
    "fed", "federal reserve", "rate", "interest", "nasdaq", "dollar",
    "inflation", "gdp", "recession", "jobs", "cpi", "tariff", "trade",
    "powell", "fomc", "treasury", "earnings",
]


def _score_news(title: str, summary: str) -> int:
    text = (title + " " + summary).lower()
    return sum(1 for kw in PRIORITY_KEYWORDS if kw in text)


def _fetch_ticker(ticker: str, period: str = "7d") -> dict | None:
    t = yf.Ticker(ticker)
    hist = t.history(period=period)
    if len(hist) < 2:
        return None
    today_close = hist["Close"].iloc[-1]
    prev_close = hist["Close"].iloc[-2]
    change = today_close - prev_close
    change_pct = (change / prev_close) * 100
    return {
        "value": round(today_close, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "date": hist.index[-1].strftime("%Y-%m-%d"),
    }


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
            return None
        latest = rows[-1]
        return {
            "value": float(latest["FEDFUNDS"]),
            "date": latest["DATE"],
        }
    except Exception:
        return None


def fetch_news(max_items: int = 8) -> list[dict]:
    items = []
    for source_name, url in NEWS_FEEDS:
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
        except Exception:
            continue

    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:max_items]
