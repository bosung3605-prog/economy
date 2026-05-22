import os
import sys
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fetchers import fetch_market_data, fetch_interest_rate, fetch_news
from report import (
    build_analysis,
    parse_analysis,
    build_hero_html,
    build_nasdaq_html,
    build_kospi_html,
    build_news_html,
    build_telegram_message,
    render_html,
)

KST = timezone(timedelta(hours=9))
DOCS_DIR = Path(__file__).parent.parent / "docs"


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, json=payload, timeout=15)
    if not resp.ok:
        print(f"텔레그램 발송 실패: {resp.status_code} {resp.text}", file=sys.stderr)
    else:
        print("텔레그램 발송 완료")


def main() -> None:
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    today = datetime.now(KST).strftime("%Y년 %m월 %d일")
    print(f"[{today}] 경제 브리핑 생성 시작")

    print("시장 데이터 수집 중...")
    market = fetch_market_data()

    print("기준금리 수집 중...")
    rate = fetch_interest_rate()

    print("한국 경제 뉴스 수집 중...")
    news_items = fetch_news(max_items=8)

    print(f"[데이터 확인] market={market}, rate={rate}, news={len(news_items)}건")

    print("AI 해설 생성 중...")
    if groq_api_key:
        raw_analysis = build_analysis(market, rate, news_items, groq_api_key)
        analysis = parse_analysis(raw_analysis)
    else:
        print("GROQ_API_KEY 미설정 — AI 해설 생략")
        analysis = {"usdkrw_reason": "", "rate_reason": "", "nasdaq_bullets": "", "korea_bullets": ""}

    hero_html = build_hero_html(market, rate, analysis)
    nasdaq_html = build_nasdaq_html(market, analysis)
    kospi_html = build_kospi_html(market, analysis)
    news_html = build_news_html(news_items)
    html = render_html(today, hero_html, nasdaq_html, kospi_html, news_html)

    DOCS_DIR.mkdir(exist_ok=True)
    html_path = DOCS_DIR / "index.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML 보고서 저장 완료: {html_path}")

    if telegram_token and telegram_chat_id:
        print("텔레그램 메시지 발송 중...")
        tg_text = build_telegram_message(today, market, rate, news_items, analysis)
        send_telegram(telegram_token, telegram_chat_id, tg_text)
    else:
        print("텔레그램 환경 변수 미설정 — 발송 건너뜀")

    print("완료")


if __name__ == "__main__":
    main()
