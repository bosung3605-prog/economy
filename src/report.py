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
  .card-title {{ font-size: 0.78rem; font-weight: 600; text-transform: uppercase;
                 letter-spacing: .06em; color: #a0aec0; margin-bottom: 14px; }}
  .three-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }}
  @media (max-width: 480px) {{ .three-col {{ grid-template-columns: 1fr; }} }}
  .hero-block {{ padding: 12px; background: #f7fafc; border-radius: 8px; }}
  .hero-label {{ font-size: 0.75rem; color: #718096; margin-bottom: 4px; }}
  .hero-number {{ font-size: 2rem; font-weight: 800; line-height: 1; }}
  .hero-unit {{ font-size: 0.9rem; font-weight: 400; }}
  .hero-change {{ font-size: 0.8rem; margin-top: 5px; }}
  .reason {{ font-size: 0.87rem; line-height: 1.7; color: #2d3748;
             background: #f7fafc; border-left: 3px solid #e2e8f0;
             padding: 10px 12px; border-radius: 0 6px 6px 0; margin-top: 10px; }}
  .divider {{ height: 1px; background: #e2e8f0; margin: 14px 0; }}
  .big-metric {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; }}
  .big-value {{ font-size: 1.9rem; font-weight: 800; }}
  .big-change {{ font-size: 0.85rem; }}
  .sub-title {{ font-size: 0.82rem; font-weight: 700; color: #4a5568;
                margin: 14px 0 6px; padding-bottom: 4px;
                border-bottom: 1px solid #e2e8f0; }}
  .bullet-list {{ padding-left: 0; list-style: none; margin-bottom: 4px; }}
  .bullet-list li {{ font-size: 0.87rem; line-height: 1.7; color: #2d3748;
                     padding: 4px 0; border-bottom: 1px solid #f7fafc; }}
  .bullet-list li:last-child {{ border-bottom: none; }}
  .bullet-list li::before {{ content: "•"; color: #4a90d9; font-weight: 700; margin-right: 8px; }}
  .bullet-pos li::before {{ content: "•"; color: #38a169; }}
  .bullet-neg li::before {{ content: "•"; color: #e53e3e; }}
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

<p class="footer">데이터: Twelve Data · FRED · 한국은행(ECOS) | AI: Groq (Llama 3.3)</p>
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


def _rate_change_label(change: float) -> str:
    if change > 0:
        return f"▲ {abs(change):.2f}%p 인상"
    if change < 0:
        return f"▼ {abs(change):.2f}%p 인하"
    return "— 동결"


def _extract_section(text: str, tag: str) -> str:
    m = re.search(rf"\[{tag}\](.*?)\[/{tag}\]", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _bullets_to_html(text: str, css_class: str = "bullet-list") -> str:
    lines = [l.strip().lstrip("•·-").strip() for l in text.splitlines() if l.strip()]
    items = "".join(f"<li>{l}</li>" for l in lines if l)
    return f'<ul class="{css_class}">{items}</ul>' if items else ""


def _company_bullets_to_html(text: str) -> str:
    """긍정:/부정: 접두어를 파싱해 색상 분리 렌더링."""
    pos_lines, neg_lines = [], []
    for line in text.splitlines():
        line = line.strip().lstrip("•·-").strip()
        if not line:
            continue
        if line.startswith("긍정"):
            pos_lines.append(re.sub(r"^긍정[:\s]*", "", line).strip())
        elif line.startswith("부정"):
            neg_lines.append(re.sub(r"^부정[:\s]*", "", line).strip())
        else:
            pos_lines.append(line)

    html = ""
    if pos_lines:
        items = "".join(f"<li>{l}</li>" for l in pos_lines)
        html += f'<div class="sub-title">긍정적 전망</div><ul class="bullet-list bullet-pos">{items}</ul>'
    if neg_lines:
        items = "".join(f"<li>{l}</li>" for l in neg_lines)
        html += f'<div class="sub-title">부정적 전망</div><ul class="bullet-list bullet-neg">{items}</ul>'
    return html


def parse_analysis(raw: str) -> dict:
    return {
        "usdkrw_reason":  _extract_section(raw, "환율이유"),
        "rate_reason":    _extract_section(raw, "금리이유"),
        "nasdaq_sector":  _extract_section(raw, "나스닥섹터"),
        "nasdaq_company": _extract_section(raw, "나스닥기업"),
        "nasdaq_outlook": _extract_section(raw, "나스닥전망"),
        "kospi_sector":   _extract_section(raw, "코스피섹터"),
        "kospi_company":  _extract_section(raw, "코스피기업"),
        "korea_outlook":  _extract_section(raw, "한국전망"),
    }


def build_hero_html(market: dict, rate: dict | None, kor_rate: dict | None, analysis: dict) -> str:
    fx = market.get("usdkrw")

    fx_html = ""
    if fx:
        cls = _css(fx["change"])
        fx_html = f"""
    <div class="hero-block">
      <div class="hero-label">달러/원 환율</div>
      <div class="hero-number {cls}">{fx['value']:,.1f}<span class="hero-unit">원</span></div>
      <div class="hero-change {cls}">{_arrow(fx['change'])} {abs(fx['change']):.1f}원 ({abs(fx['change_pct']):.2f}%) 전일比</div>
    </div>"""

    us_rate_html = ""
    if rate:
        rate_cls = _css(rate.get("change", 0))
        us_rate_html = f"""
    <div class="hero-block">
      <div class="hero-label">미국 기준금리</div>
      <div class="hero-number flat">{rate['value']:.2f}<span class="hero-unit">%</span></div>
      <div class="hero-change {rate_cls}">{_rate_change_label(rate.get('change', 0))} 전월比</div>
    </div>"""

    kor_rate_html = ""
    if kor_rate:
        kor_cls = _css(kor_rate.get("change", 0))
        kor_rate_html = f"""
    <div class="hero-block">
      <div class="hero-label">한국 기준금리</div>
      <div class="hero-number flat">{kor_rate['value']:.2f}<span class="hero-unit">%</span></div>
      <div class="hero-change {kor_cls}">{_rate_change_label(kor_rate.get('change', 0))} 전월比</div>
    </div>"""

    reason_parts = []
    if analysis.get("usdkrw_reason"):
        reason_parts.append(
            f'<div class="reason"><strong>환율 변동 이유</strong><br>{analysis["usdkrw_reason"]}</div>'
        )
    if analysis.get("rate_reason"):
        reason_parts.append(
            f'<div class="reason" style="margin-top:8px;"><strong>금리 현황</strong><br>{analysis["rate_reason"]}</div>'
        )

    reason_html = ('<div class="divider"></div>' + "".join(reason_parts)) if reason_parts else ""

    return f"""<div class="card">
  <div class="card-title">환율 &amp; 기준금리</div>
  <div class="three-col">{fx_html}{us_rate_html}{kor_rate_html}</div>
  {reason_html}
</div>"""


def build_nasdaq_html(market: dict, analysis: dict) -> str:
    n = market.get("nasdaq")
    if not n:
        return ""
    cls = _css(n["change_pct"])

    sector_html = ""
    if analysis.get("nasdaq_sector"):
        sector_html = f'<div class="sub-title">📊 주도 섹터</div>{_bullets_to_html(analysis["nasdaq_sector"])}'

    company_html = ""
    if analysis.get("nasdaq_company"):
        company_html = f'<div class="sub-title">🏢 주요 기업</div>{_company_bullets_to_html(analysis["nasdaq_company"])}'

    outlook_html = ""
    if analysis.get("nasdaq_outlook"):
        outlook_html = f'<div class="sub-title">🔭 전망 &amp; 정치</div>{_bullets_to_html(analysis["nasdaq_outlook"])}'

    return f"""<div class="card">
  <div class="card-title">나스닥</div>
  <div class="big-metric">
    <span class="big-value {cls}">{n['value']:,.2f}</span>
    <span class="big-change {cls}">{_arrow(n['change_pct'])} {abs(n['change_pct']):.2f}% ({_arrow(n['change'])}{abs(n['change']):.2f}p)</span>
  </div>
  {sector_html}
  {company_html}
  {outlook_html}
</div>"""


def build_kospi_html(market: dict, analysis: dict) -> str:
    k = market.get("kospi")
    if not k:
        return ""
    cls = _css(k["change_pct"])

    sector_html = ""
    if analysis.get("kospi_sector"):
        sector_html = f'<div class="sub-title">📊 주도 섹터</div>{_bullets_to_html(analysis["kospi_sector"])}'

    company_html = ""
    if analysis.get("kospi_company"):
        company_html = f'<div class="sub-title">🏢 주요 기업</div>{_company_bullets_to_html(analysis["kospi_company"])}'

    outlook_html = ""
    if analysis.get("korea_outlook"):
        outlook_html = f'<div class="sub-title">🔭 전망 &amp; 정치</div>{_bullets_to_html(analysis["korea_outlook"])}'

    return f"""<div class="card">
  <div class="card-title">코스피 &amp; 한국 경제</div>
  <div class="big-metric">
    <span class="big-value {cls}">{k['value']:,.2f}</span>
    <span class="big-change {cls}">{_arrow(k['change_pct'])} {abs(k['change_pct']):.2f}% ({_arrow(k['change'])}{abs(k['change']):.2f}p)</span>
  </div>
  {sector_html}
  {company_html}
  {outlook_html}
</div>"""


def build_analysis(market: dict, rate: dict | None, kor_rate: dict | None, groq_api_key: str) -> str:
    nasdaq_info = "데이터 없음"
    if market.get("nasdaq"):
        n = market["nasdaq"]
        nasdaq_info = f"{n['value']:,.2f}p ({_arrow(n['change_pct'])} {abs(n['change_pct']):.2f}%)"

    kospi_info = "데이터 없음"
    if market.get("kospi"):
        k = market["kospi"]
        kospi_info = f"{k['value']:,.2f}p ({_arrow(k['change_pct'])} {abs(k['change_pct']):.2f}%)"

    fx_info = "데이터 없음"
    if market.get("usdkrw"):
        fx = market["usdkrw"]
        fx_info = f"1달러 = {fx['value']:,.1f}원 ({_arrow(fx['change'])} {abs(fx['change']):.1f}원)"

    us_rate_info = "데이터 없음"
    if rate:
        us_rate_info = f"{rate['value']:.2f}% ({_rate_change_label(rate.get('change', 0))}, {rate['date']} 기준)"

    kor_rate_info = "데이터 없음"
    if kor_rate:
        kor_rate_info = f"{kor_rate['value']:.2f}% ({_rate_change_label(kor_rate.get('change', 0))}, {kor_rate['date']} 기준)"

    prompt = f"""당신은 10년 경력의 한국 금융 애널리스트입니다. 아래 지표를 바탕으로 심층 분석을 작성하세요.

[오늘의 지표]
- 달러/원 환율: {fx_info}
- 미국 기준금리: {us_rate_info}
- 한국 기준금리: {kor_rate_info}
- 나스닥: {nasdaq_info}
- 코스피: {kospi_info}

아래 8개 섹션을 정확히 이 형식으로 작성하세요. 태그는 반드시 유지하세요. 모호한 표현 금지.

[환율이유]
달러/원 환율 변동의 구체적 원인을 2~3문장으로 서술. 미국 달러 강약 원인(연준 기조, 경제지표)과 원화 수급(외국인 자금흐름, 수출입)을 연결해 설명.
[/환율이유]

[금리이유]
미국 기준금리: 현재 수준 배경, 인플레이션 진행 상황, 연준 향후 방향 1~2문장.
한국 기준금리: 한국은행 결정 배경, 미·한 금리 격차가 원화와 자본흐름에 미치는 영향 1~2문장.
[/금리이유]

[나스닥섹터]
나스닥을 주도하는 섹터 3~4개를 bullet point로 작성. 각 줄은 • 로 시작. 섹터명과 주도 이유를 반드시 명시(예: AI/반도체 섹터 — 엔비디아 실적 상향으로 ...).
[/나스닥섹터]

[나스닥기업]
나스닥 주요 기업의 전망을 bullet point로 작성. 각 줄은 반드시 "긍정:" 또는 "부정:" 으로 시작하고, 기업명과 구체적 이유를 명시. 긍정 3개, 부정 2~3개.
예시:
긍정: 엔비디아 — 데이터센터 수요 급증으로 2분기 실적 대폭 상향 전망
부정: 애플 — 중국 스마트폰 시장 점유율 하락, 화웨이와의 경쟁 심화
[/나스닥기업]

[나스닥전망]
나스닥 향후 3~6개월 방향성과 정부·정치적 영향을 bullet point 3~4개로 작성. 각 줄은 • 로 시작.
- 연준 통화정책 방향이 기술주에 미치는 영향
- 미국 정부의 빅테크 규제, 반도체 수출통제, 무역정책이 나스닥에 미치는 영향
- 주목해야 할 리스크 또는 기회 요인
[/나스닥전망]

[코스피섹터]
코스피를 주도하는 섹터 3~4개를 bullet point로 작성. 각 줄은 • 로 시작. 섹터명과 주도 이유 반드시 명시(예: 반도체 섹터 — 삼성전자·SK하이닉스 HBM 수요 호조로 ...).
[/코스피섹터]

[코스피기업]
코스피 주요 기업의 전망을 bullet point로 작성. 각 줄은 반드시 "긍정:" 또는 "부정:" 으로 시작. 기업명 반드시 명시. 긍정 3개, 부정 2~3개.
예시:
긍정: 삼성전자 — HBM3E 공급 계약 확대로 반도체 부문 실적 회복 기대
부정: LG에너지솔루션 — 전기차 수요 둔화로 배터리 출하량 감소 우려
[/코스피기업]

[한국전망]
코스피 향후 3~6개월 방향성과 한국 정부·정치적 영향을 bullet point 3~4개로 작성. 각 줄은 • 로 시작.
- 한국 정부 산업정책(반도체 지원, 수출 규제 대응, 재정정책)이 코스피에 미치는 영향
- 외국인 투자자 수급 전망 및 원화 환율 영향
- 주목해야 할 리스크 또는 기회 요인
[/한국전망]

모든 내용은 한국어로 작성하세요. 기업명·섹터명은 반드시 구체적으로 명시하세요."""

    try:
        client = Groq(api_key=groq_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2800,
            temperature=0.25,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        empty = "[/환율이유][금리이유][/금리이유][나스닥섹터][/나스닥섹터][나스닥기업][/나스닥기업][나스닥전망][/나스닥전망][코스피섹터][/코스피섹터][코스피기업][/코스피기업][한국전망][/한국전망]"
        return f"[환율이유]AI 해설 오류: {e}{empty}"


def build_telegram_message(date: str, market: dict, rate: dict | None, kor_rate: dict | None, analysis: dict) -> str:
    lines = [f"📊 *오늘의 경제 브리핑* — {date}\n"]

    if market.get("usdkrw"):
        fx = market["usdkrw"]
        arrow = "🔴" if fx["change"] > 0 else "🟢"
        lines.append(f"{arrow} *달러/원*: {fx['value']:,.1f}원 ({_arrow(fx['change'])}{abs(fx['change']):.1f}원)")
    if rate:
        lines.append(f"🏦 *미국 금리*: {rate['value']:.2f}% ({_rate_change_label(rate.get('change', 0))})")
    if kor_rate:
        lines.append(f"🏦 *한국 금리*: {kor_rate['value']:.2f}% ({_rate_change_label(kor_rate.get('change', 0))})")
    if market.get("nasdaq"):
        n = market["nasdaq"]
        arrow = "🔴" if n["change_pct"] < 0 else "🟢"
        lines.append(f"{arrow} *나스닥*: {n['value']:,.2f}p ({_arrow(n['change_pct'])}{abs(n['change_pct']):.2f}%)")
    if market.get("kospi"):
        k = market["kospi"]
        arrow = "🔴" if k["change_pct"] < 0 else "🟢"
        lines.append(f"{arrow} *코스피*: {k['value']:,.2f}p ({_arrow(k['change_pct'])}{abs(k['change_pct']):.2f}%)")

    if analysis.get("usdkrw_reason"):
        lines.append(f"\n💱 *환율*\n{analysis['usdkrw_reason'][:250]}")
    if analysis.get("rate_reason"):
        lines.append(f"\n🏦 *금리*\n{analysis['rate_reason'][:250]}")

    if analysis.get("nasdaq_sector"):
        bullets = [l.strip() for l in analysis["nasdaq_sector"].splitlines() if l.strip()][:3]
        lines.append("\n📈 *나스닥 주도 섹터*\n" + "\n".join(bullets))

    if analysis.get("nasdaq_outlook"):
        bullets = [l.strip() for l in analysis["nasdaq_outlook"].splitlines() if l.strip()][:2]
        lines.append("\n🔭 *나스닥 전망*\n" + "\n".join(bullets))

    if analysis.get("kospi_sector"):
        bullets = [l.strip() for l in analysis["kospi_sector"].splitlines() if l.strip()][:3]
        lines.append("\n📉 *코스피 주도 섹터*\n" + "\n".join(bullets))

    if analysis.get("korea_outlook"):
        bullets = [l.strip() for l in analysis["korea_outlook"].splitlines() if l.strip()][:2]
        lines.append("\n🇰🇷 *한국 전망*\n" + "\n".join(bullets))

    return "\n".join(lines)


def render_html(date: str, hero_html: str, nasdaq_html: str, kospi_html: str) -> str:
    return HTML_TEMPLATE.format(
        date=date,
        hero_html=hero_html,
        nasdaq_html=nasdaq_html,
        kospi_html=kospi_html,
    )
