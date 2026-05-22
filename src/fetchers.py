import requests
import feedparser
import yfinance as yf
from datetime import datetime, timedelta
import io
import csv

NASDAQ_TICKER = "^IXIC"
USD_KRW_TICKER = "USDKRW=X"
FRED_FEDFUNDS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS"

NEWS_FEEDS = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
]

# 환율/금리/나스닥에 영향 주는 키워드 우선 필터
PRIORITY_KEYWORDS = [
    "fed", "federal reserve", "rate", "interest", "inflation", "nasdaq",
    "dollar", "currency", "exchange", "gdp", "recession", "jobs", "employment",
    "cpi", "tariff", "trade", "earnings", "powell", "fomc", "treasury",
    "금리", "환율", "연준", "인플레이션", "나스닥", "달러",
]


def _score_news(title: str, summary: str) -> int:
    text = (title + " " + summary).lower()
    return sum(1 for kw in PRIORITY_KEYWORDS if kw in text)


def fetch_market_data() -> dict:
    result = {}

    # 나스닥
    nasdaq = yf.Ticker(NASDAQ_TICKER)
    hist = nasdaq.history(period="5d")
    if len(hist) >= 2:
        today_close = hist["Close"].iloc[-1]
        prev_close = hist["Close"].iloc[-2]
        change = today_close - prev_close
        change_pct = (change / prev_close) * 100
        result["nasdaq"] = {
            "value": round(today_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "date": hist.index[-1].strftime("%Y-%m-%d"),
        }
    else:
        result["nasdaq"] = None

    # 달러/원 환율
    usdkrw = yf.Ticker(USD_KRW_TICKER)
    hist_fx = usdkrw.history(period="5d")
    if len(hist_fx) >= 2:
        today_rate = hist_fx["Close"].iloc[-1]
        prev_rate = hist_fx["Close"].iloc[-2]
        change = today_rate - prev_rate
        change_pct = (change / prev_rate) * 100
        result["usdkrw"] = {
            "value": round(today_rate, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "date": hist_fx.index[-1].strftime("%Y-%m-%d"),
        }
    else:
        result["usdkrw"] = None

    return result


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
