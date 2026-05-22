import os
from datetime import datetime
from groq import Groq

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>오늘의 경제 브리핑 — {date}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f0f4f8; color: #1a202c; padding: 16px; }}
  h1 {{ font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }}
  .subtitle {{ color: #718096; font-size: 0.85rem; margin-bottom: 20px; }}
  .card {{ background: #fff; border-radius: 12px; padding: 16px;
           margin-bottom: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .card h2 {{ font-size: 1rem; font-weight: 600; margin-bottom: 12px;
              color: #2d3748; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
  .metric {{ display: flex; justify-content: space-between; align-items: center;
             padding: 8px 0; border-bottom: 1px solid #f7fafc; }}
  .metric:last-child {{ border-bottom: none; }}
  .metric-label {{ font-size: 0.9rem; color: #4a5568; }}
  .metric-value {{ font-size: 1.1rem; font-weight: 700; }}
  .metric-change {{ font-size: 0.78rem; margin-left: 6px; }}
  .up {{ color: #e53e3e; }}
  .down {{ color: #3182ce; }}
  .flat {{ color: #718096; }}
  .news-item {{ padding: 8px 0; border-bottom: 1px solid #f7fafc; }}
  .news-item:last-child {{ border-bottom: none; }}
  .news-source {{ font-size: 0.72rem; color: #a0aec0; margin-bottom: 2px; }}
  .news-title a {{ font-size: 0.88rem; color: #2b6cb0; text-decoration: none; line-height: 1.4; }}
  .news-title a:hover {{ text-decoration: underline; }}
  .analysis {{ white-space: pre-line; font-size: 0.9rem; line-height: 1.7;
               color: #2d3748; background: #f7fafc; border-radius: 8px;
               padding: 12px; margin-top: 4px; }}
  .footer {{ text-align: center; font-size: 0.75rem; color: #a0aec0; margin-top: 16px; }}
</style>
</head>
<body>
<h1>오늘의 경제 브리핑</h1>
<p class="subtitle">{date} 기준 · 매일 오전 7시 자동 업데이트</p>

<div class="card">
  <h2>시장 지표</h2>
  {metrics_html}
</div>

<div class="card">
  <h2>오늘의 경제 뉴스</h2>
  {news_html}
</div>

<div class="card">
  <h2>중학생도 이해하는 오늘의 해설</h2>
  <div class="analysis">{analysis}</div>
</div>

<p class="footer">데이터 출처: Yahoo Finance · FRED · Reuters · BBC | AI 해설: Groq (Llama 3.3)</p>
</body>
</html>"""


def _arrow(change: float) -> str:
    if change > 0:
        return "▲"
    if change < 0:
        return "▼"
    return "—"


def _css_class(change: float) -> str:
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return "flat"


def build_metrics_html(market: dict, rate: dict | None) -> str:
    rows = []

    if market.get("nasdaq"):
        n = market["nasdaq"]
        cls = _css_class(n["change_pct"])
        rows.append(
            f'<div class="metric">'
            f'<span class="metric-label">나스닥 지수</span>'
            f'<span class="metric-value {cls}">{n["value"]:,.2f}'
            f'<span class="metric-change {cls}">{_arrow(n["change_pct"])} {abs(n["change_pct"]):.2f}%</span>'
            f"</span></div>"
        )

    if market.get("usdkrw"):
        fx = market["usdkrw"]
        cls = _css_class(fx["change"])
        rows.append(
            f'<div class="metric">'
            f'<span class="metric-label">달러/원 환율</span>'
            f'<span class="metric-value {cls}">{fx["value"]:,.2f}원'
            f'<span class="metric-change {cls}">{_arrow(fx["change"])} {abs(fx["change"]):.2f}원</span>'
            f"</span></div>"
        )

    if rate:
        rows.append(
            f'<div class="metric">'
            f'<span class="metric-label">미국 기준금리 (Fed Funds)</span>'
            f'<span class="metric-value flat">{rate["value"]:.2f}%'
            f'<span class="metric-change flat">({rate["date"]} 기준)</span>'
            f"</span></div>"
        )

    return "\n".join(rows) if rows else "<p>데이터를 불러올 수 없습니다.</p>"


def build_news_html(news_items: list[dict]) -> str:
    if not news_items:
        return "<p>뉴스를 불러올 수 없습니다.</p>"
    rows = []
    for item in news_items:
        link = item["link"]
        title = item["title"]
        source = item["source"]
        rows.append(
            f'<div class="news-item">'
            f'<div class="news-source">{source}</div>'
            f'<div class="news-title"><a href="{link}" target="_blank">{title}</a></div>'
            f"</div>"
        )
    return "\n".join(rows)


def build_analysis(market: dict, rate: dict | None, news_items: list[dict], groq_api_key: str) -> str:
    headlines = "\n".join(f"- {n['title']}" for n in news_items[:6])

    nasdaq_info = "데이터 없음"
    if market.get("nasdaq"):
        n = market["nasdaq"]
        direction = "올랐고" if n["change_pct"] > 0 else "내렸고"
        nasdaq_info = f"{n['value']:,.0f}p ({_arrow(n['change_pct'])} {abs(n['change_pct']):.2f}% {direction})"

    fx_info = "데이터 없음"
    if market.get("usdkrw"):
        fx = market["usdkrw"]
        direction = "올랐습니다" if fx["change"] > 0 else "내렸습니다"
        fx_info = f"1달러 = {fx['value']:,.1f}원 (전일 대비 {_arrow(fx['change'])} {abs(fx['change']):.1f}원 {direction})"

    rate_info = f"{rate['value']:.2f}%" if rate else "데이터 없음"

    prompt = f"""오늘의 경제 지표와 뉴스를 중학생(13~15세)도 이해할 수 있도록 한국어로 쉽게 설명해주세요.

[오늘의 지표]
- 나스닥: {nasdaq_info}
- 달러/원 환율: {fx_info}
- 미국 기준금리: {rate_info}

[오늘의 주요 뉴스 헤드라인]
{headlines}

다음 형식으로 작성해주세요:
1. 오늘 시장 전체 분위기 (2~3문장)
2. 나스닥이 왜 올랐는지/내렸는지 — 뉴스와 연결해서 설명 (2~3문장)
3. 환율 변화가 우리 생활에 미치는 영향 (2문장)
4. 기준금리가 지금 수준인 이유와 앞으로 영향 (2문장)

전문 용어가 나오면 괄호 안에 쉬운 설명을 꼭 붙여주세요. 친근한 말투로 써주세요."""

    try:
        client = Groq(api_key=groq_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI 해설을 불러오지 못했습니다. ({e})"


def build_telegram_message(date: str, market: dict, rate: dict | None, news_items: list[dict], analysis: str) -> str:
    lines = [f"📊 *오늘의 경제 브리핑* — {date}\n"]

    if market.get("nasdaq"):
        n = market["nasdaq"]
        arrow = "🔴" if n["change_pct"] < 0 else "🟢"
        lines.append(f"{arrow} *나스닥*: {n['value']:,.2f}p ({_arrow(n['change_pct'])}{abs(n['change_pct']):.2f}%)")

    if market.get("usdkrw"):
        fx = market["usdkrw"]
        arrow = "🔴" if fx["change"] > 0 else "🟢"
        lines.append(f"{arrow} *달러/원*: {fx['value']:,.1f}원 ({_arrow(fx['change'])}{abs(fx['change']):.1f}원)")

    if rate:
        lines.append(f"🏦 *기준금리*: {rate['value']:.2f}% ({rate['date']} 기준)")

    lines.append("\n📰 *주요 뉴스*")
    for item in news_items[:5]:
        title = item["title"][:60] + ("..." if len(item["title"]) > 60 else "")
        lines.append(f"• [{title}]({item['link']})")

    lines.append(f"\n💡 *해설*\n{analysis[:800]}")

    return "\n".join(lines)


def render_html(date: str, metrics_html: str, news_html: str, analysis: str) -> str:
    return HTML_TEMPLATE.format(
        date=date,
        metrics_html=metrics_html,
        news_html=news_html,
        analysis=analysis,
    )
