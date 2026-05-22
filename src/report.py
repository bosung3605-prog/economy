import re
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
  .card {{ background: #fff; border-radius: 12px; padding: 18px;
           margin-bottom: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .card-title {{ font-size: 0.8rem; font-weight: 600; text-transform: uppercase;
                 letter-spacing: .06em; color: #a0aec0; margin-bottom: 14px; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .hero-block {{ padding: 12px; background: #f7fafc; border-radius: 8px; }}
  .hero-label {{ font-size: 0.78rem; color: #718096; margin-bottom: 4px; }}
  .hero-number {{ font-size: 2.2rem; font-weight: 800; line-height: 1; }}
  .hero-change {{ font-size: 0.82rem; margin-top: 4px; }}
  .reason {{ font-size: 0.87rem; line-height: 1.7; color: #2d3748;
             background: #f7fafc; border-left: 3px solid #e2e8f0;
             padding: 10px 12px; border-radius: 0 6px 6px 0; margin-top: 10px; }}
  .divider {{ height: 1px; background: #e2e8f0; margin: 14px 0; }}
  .big-metric {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px; }}
  .big-value {{ font-size: 1.9rem; font-weight: 800; }}
  .big-change {{ font-size: 0.85rem; }}
  .bullet-list {{ margin-top: 10px; padding-left: 0; list-style: none; }}
  .bullet-list li {{ font-size: 0.87rem; line-height: 1.7; color: #2d3748;
                     padding: 5px 0; border-bottom: 1px solid #f0f4f8; }}
  .bullet-list li:last-child {{ border-bottom: none; }}
  .bullet-list li::before {{ content: "•"; color: #4a90d9; font-weight: 700;
                              margin-right: 8px; }}
  .news-item {{ padding: 8px 0; border-bottom: 1px solid #f7fafc; }}
  .news-item:last-child {{ border-bottom: none; }}
  .news-source {{ font-size: 0.72rem; color: #a0aec0; margin-bottom: 2px; }}
  .news-title a {{ font-size: 0.88rem; color: #2b6cb0; text-decoration: none; line-height: 1.4; }}
  .news-title a:hover {{ text-decoration: underline; }}
  .up {{ color: #e53e3e; }}
  .down {{ color: #3182ce; }}
  .flat {{ color: #718096; }}
  .footer {{ text-align: center; font-size: 0.75rem; color: #a0aec0; margin-top: 16px; }}
</style>
</head>
<body>
<h1>오늘의 경제 브리핑</h1>
<p class="subtitle">{date} 기준 · 매일 오전 7시 자동 업데이트</p>

{hero_html}
{nasdaq_html}
{kospi_html}

<div class="card">
  <div class="card-title">오늘의 한국 경제 뉴스</div>
  {news_html}
</div>

<p class="footer">데이터: Yahoo Finance · FRED · 한국경제 · 매일경제 · 연합뉴스 | AI: Groq (Llama 3.3)</p>
</body>
</html>"""


def _arrow(change: float) -> str:
    if change > 0:
        return "▲"
    if change < 0:
        return "▼"
    return "—"


def _css(change: float) -> str:
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return "flat"


def _extract_section(text: str, tag: str) -> str:
    m = re.search(rf"\[{tag}\](.*?)\[/{tag}\]", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _bullets_to_html(text: str) -> str:
    lines = [l.strip().lstrip("•·-").strip() for l in text.splitlines() if l.strip()]
    return "".join(f"<li>{l}</li>" for l in lines if l)


def parse_analysis(raw: str) -> dict:
    return {
        "usdkrw_reason": _extract_section(raw, "환율이유"),
        "rate_reason": _extract_section(raw, "금리이유"),
        "nasdaq_bullets": _extract_section(raw, "나스닥분석"),
        "korea_bullets": _extract_section(raw, "한국경제"),
    }


def build_hero_html(market: dict, rate: dict | None, analysis: dict) -> str:
    fx = market.get("usdkrw")
    fx_html = ""
    if fx:
        cls = _css(fx["change"])
        fx_html = f"""
    <div class="hero-block">
      <div class="hero-label">달러/원 환율</div>
      <div class="hero-number {cls}">{fx['value']:,.1f}<span style="font-size:1rem;font-weight:400;">원</span></div>
      <div class="hero-change {cls}">{_arrow(fx['change'])} {abs(fx['change']):.1f}원 ({abs(fx['change_pct']):.2f}%)</div>
    </div>"""

    rate_html = ""
    if rate:
        rate_html = f"""
    <div class="hero-block">
      <div class="hero-label">미국 기준금리 (Fed Funds)</div>
      <div class="hero-number flat">{rate['value']:.2f}<span style="font-size:1rem;font-weight:400;">%</span></div>
      <div class="hero-change flat">{rate['date']} 기준</div>
    </div>"""

    usdkrw_reason = analysis.get("usdkrw_reason", "")
    rate_reason = analysis.get("rate_reason", "")

    reason_html = ""
    if usdkrw_reason or rate_reason:
        reason_html = '<div class="divider"></div>'
        if usdkrw_reason:
            reason_html += f'<div class="reason"><strong>환율 변동 이유</strong><br>{usdkrw_reason}</div>'
        if rate_reason:
            reason_html += f'<div class="reason" style="margin-top:8px;"><strong>금리 현황</strong><br>{rate_reason}</div>'

    return f"""<div class="card">
  <div class="card-title">환율 &amp; 금리</div>
  <div class="two-col">{fx_html}{rate_html}</div>
  {reason_html}
</div>"""


def build_nasdaq_html(market: dict, analysis: dict) -> str:
    n = market.get("nasdaq")
    if not n:
        return ""
    cls = _css(n["change_pct"])
    bullets = _bullets_to_html(analysis.get("nasdaq_bullets", ""))
    bullets_block = f'<ul class="bullet-list">{bullets}</ul>' if bullets else ""

    return f"""<div class="card">
  <div class="card-title">나스닥</div>
  <div class="big-metric">
    <span class="big-value {cls}">{n['value']:,.2f}</span>
    <span class="big-change {cls}">{_arrow(n['change_pct'])} {abs(n['change_pct']):.2f}% ({_arrow(n['change'])}{abs(n['change']):.2f}p)</span>
  </div>
  {bullets_block}
</div>"""


def build_kospi_html(market: dict, analysis: dict) -> str:
    k = market.get("kospi")
    if not k:
        return ""
    cls = _css(k["change_pct"])
    bullets = _bullets_to_html(analysis.get("korea_bullets", ""))
    bullets_block = f'<ul class="bullet-list">{bullets}</ul>' if bullets else ""

    return f"""<div class="card">
  <div class="card-title">코스피 &amp; 한국 경제</div>
  <div class="big-metric">
    <span class="big-value {cls}">{k['value']:,.2f}</span>
    <span class="big-change {cls}">{_arrow(k['change_pct'])} {abs(k['change_pct']):.2f}% ({_arrow(k['change'])}{abs(k['change']):.2f}p)</span>
  </div>
  {bullets_block}
</div>"""


def build_news_html(news_items: list[dict]) -> str:
    if not news_items:
        return "<p>뉴스를 불러올 수 없습니다.</p>"
    rows = []
    for item in news_items:
        rows.append(
            f'<div class="news-item">'
            f'<div class="news-source">{item["source"]}</div>'
            f'<div class="news-title"><a href="{item["link"]}" target="_blank">{item["title"]}</a></div>'
            f"</div>"
        )
    return "\n".join(rows)


def build_analysis(market: dict, rate: dict | None, news_items: list[dict], groq_api_key: str) -> str:
    headlines = "\n".join(f"- {n['title']}" for n in news_items[:8])

    nasdaq_info = "데이터 없음"
    if market.get("nasdaq"):
        n = market["nasdaq"]
        direction = "상승" if n["change_pct"] > 0 else "하락"
        nasdaq_info = f"{n['value']:,.2f}p ({_arrow(n['change_pct'])} {abs(n['change_pct']):.2f}%, {direction})"

    kospi_info = "데이터 없음"
    if market.get("kospi"):
        k = market["kospi"]
        direction = "상승" if k["change_pct"] > 0 else "하락"
        kospi_info = f"{k['value']:,.2f}p ({_arrow(k['change_pct'])} {abs(k['change_pct']):.2f}%, {direction})"

    fx_info = "데이터 없음"
    if market.get("usdkrw"):
        fx = market["usdkrw"]
        direction = "상승" if fx["change"] > 0 else "하락"
        fx_info = f"1달러 = {fx['value']:,.1f}원 (전일 대비 {_arrow(fx['change'])} {abs(fx['change']):.1f}원, {direction})"

    rate_info = f"{rate['value']:.2f}% ({rate['date']} 기준)" if rate else "데이터 없음"

    prompt = f"""아래 경제 지표와 한국 경제 뉴스를 바탕으로 분석을 작성해주세요.

[오늘의 지표]
- 달러/원 환율: {fx_info}
- 미국 기준금리: {rate_info}
- 나스닥: {nasdaq_info}
- 코스피: {kospi_info}

[오늘의 한국 경제 뉴스 헤드라인]
{headlines}

아래 4개 섹션을 정확히 이 형식으로 작성하세요. 태그는 그대로 유지하세요.

[환율이유]
환율이 왜 올랐는지/내렸는지 구체적으로 설명하세요. "복잡하다", "불확실하다" 같은 모호한 표현 금지. 반드시 구체적인 원인(예: 미국 금리 결정, 수출 지표, 달러 강세 원인)을 2~3문장으로 서술하세요.
[/환율이유]

[금리이유]
현재 금리 수준인 이유와 향후 방향을 구체적으로 설명하세요. 연준의 최근 입장이나 경제 지표를 근거로 2~3문장으로 서술하세요.
[/금리이유]

[나스닥분석]
나스닥 변동 원인과 한국 경제에 미치는 영향을 bullet point 3~5개로 작성하세요. 각 줄은 • 로 시작하고, 모호한 표현 없이 구체적인 내용으로 작성하세요.
[/나스닥분석]

[한국경제]
코스피 흐름과 오늘 한국 경제의 핵심 이슈를 bullet point 3~5개로 작성하세요. 뉴스 헤드라인을 반드시 반영하고, 각 줄은 • 로 시작하세요.
[/한국경제]

모든 내용은 한국어로 작성하세요."""

    try:
        client = Groq(api_key=groq_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[환율이유]AI 해설을 불러오지 못했습니다. ({e})[/환율이유][금리이유][/금리이유][나스닥분석][/나스닥분석][한국경제][/한국경제]"


def build_telegram_message(date: str, market: dict, rate: dict | None, news_items: list[dict], analysis: dict) -> str:
    lines = [f"📊 *오늘의 경제 브리핑* — {date}\n"]

    if market.get("usdkrw"):
        fx = market["usdkrw"]
        arrow = "🔴" if fx["change"] > 0 else "🟢"
        lines.append(f"{arrow} *달러/원*: {fx['value']:,.1f}원 ({_arrow(fx['change'])}{abs(fx['change']):.1f}원)")

    if rate:
        lines.append(f"🏦 *기준금리*: {rate['value']:.2f}% ({rate['date']} 기준)")

    if market.get("nasdaq"):
        n = market["nasdaq"]
        arrow = "🔴" if n["change_pct"] < 0 else "🟢"
        lines.append(f"{arrow} *나스닥*: {n['value']:,.2f}p ({_arrow(n['change_pct'])}{abs(n['change_pct']):.2f}%)")

    if market.get("kospi"):
        k = market["kospi"]
        arrow = "🔴" if k["change_pct"] < 0 else "🟢"
        lines.append(f"{arrow} *코스피*: {k['value']:,.2f}p ({_arrow(k['change_pct'])}{abs(k['change_pct']):.2f}%)")

    usdkrw_reason = analysis.get("usdkrw_reason", "")
    if usdkrw_reason:
        lines.append(f"\n💱 *환율 변동 이유*\n{usdkrw_reason[:300]}")

    nasdaq_bullets = analysis.get("nasdaq_bullets", "")
    if nasdaq_bullets:
        bullet_lines = [l.strip() for l in nasdaq_bullets.splitlines() if l.strip()][:3]
        lines.append("\n📈 *나스닥 분석*")
        lines.extend(bullet_lines)

    korea_bullets = analysis.get("korea_bullets", "")
    if korea_bullets:
        bullet_lines = [l.strip() for l in korea_bullets.splitlines() if l.strip()][:3]
        lines.append("\n🇰🇷 *한국 경제*")
        lines.extend(bullet_lines)

    lines.append("\n📰 *주요 뉴스*")
    for item in news_items[:4]:
        title = item["title"][:60] + ("..." if len(item["title"]) > 60 else "")
        lines.append(f"• [{title}]({item['link']})")

    return "\n".join(lines)


def render_html(date: str, hero_html: str, nasdaq_html: str, kospi_html: str, news_html: str) -> str:
    return HTML_TEMPLATE.format(
        date=date,
        hero_html=hero_html,
        nasdaq_html=nasdaq_html,
        kospi_html=kospi_html,
        news_html=news_html,
    )
