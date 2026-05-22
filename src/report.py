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
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }}
  @media (max-width: 480px) {{
    .three-col, .two-col {{ grid-template-columns: 1fr; }}
  }}
  .hero-block {{ padding: 12px; background: #f7fafc; border-radius: 8px; }}
  .hero-label {{ font-size: 0.75rem; color: #718096; margin-bottom: 4px; }}
  .hero-number {{ font-size: 2rem; font-weight: 800; line-height: 1; }}
  .hero-unit {{ font-size: 0.9rem; font-weight: 400; }}
  .hero-change {{ font-size: 0.8rem; margin-top: 5px; }}
  .reason {{ font-size: 0.87rem; line-height: 1.7; color: #2d3748;
             background: #f7fafc; border-left: 3px solid #e2e8f0;
             padding: 10px 12px; border-radius: 0 6px 6px 0; margin-top: 10px; }}
  .divider {{ height: 1px; background: #e2e8f0; margin: 14px 0; }}
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
        "kospi_outlook":  _extract_section(raw, "코스피전망"),
    }


def build_hero_html(market: dict, rate: dict | None, kor_rate: dict | None, analysis: dict) -> str:
    fx = market.get("usdkrw")
    nasdaq = market.get("nasdaq")
    kospi = market.get("kospi")

    # 행 1: 환율 | 미국금리 | 한국금리
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

    # 행 2: 나스닥 | 코스피
    nasdaq_html = ""
    if nasdaq:
        cls = _css(nasdaq["change_pct"])
        nasdaq_html = f"""
    <div class="hero-block">
      <div class="hero-label">나스닥</div>
      <div class="hero-number {cls}">{nasdaq['value']:,.2f}<span class="hero-unit">p</span></div>
      <div class="hero-change {cls}">{_arrow(nasdaq['change_pct'])} {abs(nasdaq['change_pct']):.2f}% ({_arrow(nasdaq['change'])}{abs(nasdaq['change']):.2f}p) 전일比</div>
    </div>"""

    kospi_html = ""
    if kospi:
        cls = _css(kospi["change_pct"])
        kospi_html = f"""
    <div class="hero-block">
      <div class="hero-label">코스피</div>
      <div class="hero-number {cls}">{kospi['value']:,.2f}<span class="hero-unit">p</span></div>
      <div class="hero-change {cls}">{_arrow(kospi['change_pct'])} {abs(kospi['change_pct']):.2f}% ({_arrow(kospi['change'])}{abs(kospi['change']):.2f}p) 전일比</div>
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
  <div class="card-title">오늘의 시장 지표</div>
  <div class="three-col">{fx_html}{us_rate_html}{kor_rate_html}</div>
  <div class="two-col">{nasdaq_html}{kospi_html}</div>
  {reason_html}
</div>"""


def build_nasdaq_html(market: dict, analysis: dict) -> str:
    if not market.get("nasdaq"):
        return ""

    sector_html = ""
    if analysis.get("nasdaq_sector"):
        sector_html = f'<div class="sub-title">📊 시장 방향 &amp; 주도 섹터</div>{_bullets_to_html(analysis["nasdaq_sector"])}'

    company_html = ""
    if analysis.get("nasdaq_company"):
        company_html = f'<div class="sub-title">🏢 주요 기업 이슈</div>{_company_bullets_to_html(analysis["nasdaq_company"])}'

    outlook_html = ""
    if analysis.get("nasdaq_outlook"):
        outlook_html = f'<div class="sub-title">🔭 전망 &amp; 정치</div>{_bullets_to_html(analysis["nasdaq_outlook"])}'

    return f"""<div class="card">
  <div class="card-title">나스닥 분석</div>
  {sector_html}
  {company_html}
  {outlook_html}
</div>"""


def build_kospi_html(market: dict, analysis: dict) -> str:
    if not market.get("kospi"):
        return ""

    sector_html = ""
    if analysis.get("kospi_sector"):
        sector_html = f'<div class="sub-title">📊 시장 방향 &amp; 주도 섹터</div>{_bullets_to_html(analysis["kospi_sector"])}'

    company_html = ""
    if analysis.get("kospi_company"):
        company_html = f'<div class="sub-title">🏢 주요 기업 이슈</div>{_company_bullets_to_html(analysis["kospi_company"])}'

    outlook_html = ""
    if analysis.get("kospi_outlook"):
        outlook_html = f'<div class="sub-title">🔭 코스피 전망 &amp; 정치</div>{_bullets_to_html(analysis["kospi_outlook"])}'

    return f"""<div class="card">
  <div class="card-title">코스피 분석</div>
  {sector_html}
  {company_html}
  {outlook_html}
</div>"""


def build_analysis(
    market: dict,
    rate: dict | None,
    kor_rate: dict | None,
    news_items: list[dict],
    groq_api_key: str,
) -> str:
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

    headlines = "\n".join(f"- [{n['source']}] {n['title']}" for n in news_items) if news_items else "뉴스 없음"

    prompt = f"""당신은 10년 경력의 한국 금융 애널리스트입니다. 아래 지표와 오늘의 뉴스 헤드라인을 바탕으로 심층 분석을 작성하세요.

[오늘의 지표]
- 달러/원 환율: {fx_info}
- 미국 기준금리: {us_rate_info}
- 한국 기준금리: {kor_rate_info}
- 나스닥: {nasdaq_info}
- 코스피: {kospi_info}

[오늘의 주요 뉴스 헤드라인]
{headlines}

위 뉴스 헤드라인을 반드시 반영해 [나스닥기업], [코스피기업], [나스닥전망], [코스피전망] 섹션에서 구체적 기업 이슈를 언급하세요.
아래 8개 섹션을 정확히 이 형식으로 작성하세요. 태그는 반드시 유지하세요. 모호한 표현 금지.

[환율이유]
달러/원 환율 변동의 구체적 원인을 2~3문장으로 서술. 미국 달러 강약 원인(연준 기조, 경제지표)과 원화 수급(외국인 자금흐름, 수출입)을 연결해 설명.
[/환율이유]

[금리이유]
미국 기준금리: 현재 수준 배경, 인플레이션 진행 상황, 연준 향후 방향 1~2문장.
한국 기준금리: 한국은행 결정 배경, 미·한 금리 격차가 원화와 자본흐름에 미치는 영향 1~2문장.
[/금리이유]

[나스닥섹터]
첫 번째 bullet은 반드시 오늘 나스닥이 왜 강세/약세인지 전체 시장 방향과 핵심 원인을 한 문장으로 설명하세요(예: • 오늘 나스닥은 연준 금리 동결 기대감과 AI 섹터 실적 호조로 강세). 이후 bullet 2~4개는 주도 섹터명과 이유를 명시하세요. 각 줄은 • 로 시작.
[/나스닥섹터]

[나스닥기업]
오늘 뉴스 헤드라인을 반영해 나스닥 주요 기업의 이슈와 전망을 bullet point로 작성. 각 줄은 반드시 "긍정:" 또는 "부정:" 으로 시작. 기업명과 구체적 이슈(뉴스 기반) 명시. 긍정 3개, 부정 2~3개.
예시: 긍정: 엔비디아 — 블랙웰 GPU 수요 급증으로 2분기 가이던스 대폭 상향
[/나스닥기업]

[나스닥전망]
나스닥 향후 3~6개월 전망을 6개 bullet로 작성. 각 줄은 • 로 시작하고, 각 bullet은 2~4문장으로 구체적 내용을 담으세요. 한 줄에 한 bullet로 작성하세요. 반드시 아래 6개 항목 순서대로 작성:

• (주도 섹터 + 수요/공급 분석) 현재 나스닥을 이끄는 섹터(예: AI/반도체, 클라우드, 빅테크)가 왜 강세인지를 수요·공급 구조로 설명. 예: 메모리 수요가 공급을 초과하고 있다, AI 인프라 capex가 ○○억 달러 규모로 확대되고 있다 등 구체적 동인.

• (직접 수혜 기업 + 주가 전망) 그 섹터에서 직접 수혜를 받는 미국 기업 2~3개(예: 엔비디아·AMD·브로드컴·마이크로소프트)를 실명으로 거론. 각 기업의 향후 주가 방향성과 근거(가이던스·수주 잔고·기술 우위 등).

• (파생·연관 섹터) 주도 섹터의 성장이 어떤 인접 섹터(데이터센터, 전력 인프라, 냉각 솔루션, 반도체 장비)의 수요를 만들어내는지 인과 관계 설명.

• (파생 섹터 기업명 + 전망) 파생 섹터의 미국 상장 기업 2~3개(예: 버티브, 콘스텔레이션 에너지, 이튼, 슈나이더 일렉트릭) 실명 거론. 각 기업의 주가 전망 근거.

• (주요 계약·파트너십·실적) 뉴스 헤드라인에서 확인된 또는 시장에 알려진 구체적 계약·파트너십·실적 가이던스. 회사명·상대방·계약 규모 또는 매출/영업이익 예상 수치 명시.

• (미국 정부·정치 영향 + 핵심 리스크) 연준 통화정책 방향, 빅테크 반독점 규제, 대중 반도체 수출통제, 무역·관세 정책이 나스닥에 미치는 영향. 가장 주의해야 할 리스크 1~2개 명시.
[/나스닥전망]

[코스피섹터]
첫 번째 bullet은 반드시 오늘 코스피가 왜 강세/약세인지 전체 시장 방향과 핵심 원인을 한 문장으로 설명하세요(예: • 오늘 코스피는 외국인 순매수 전환과 반도체 업황 회복 기대로 강세). 이후 bullet 2~4개는 주도 섹터명과 이유를 명시하세요. 각 줄은 • 로 시작.
[/코스피섹터]

[코스피기업]
오늘 뉴스 헤드라인을 반영해 코스피 주요 기업의 이슈와 전망을 bullet point로 작성. 각 줄은 반드시 "긍정:" 또는 "부정:" 으로 시작. 기업명과 구체적 이슈(뉴스 기반) 명시. 긍정 3개, 부정 2~3개.
예시: 부정: 삼성전자 — 노조 파업으로 반도체 라인 가동률 하락 우려
[/코스피기업]

[코스피전망]
코스피 향후 3~6개월 전망을 6개 bullet로 작성. 각 줄은 • 로 시작하고, 각 bullet은 2~4문장으로 구체적 내용을 담으세요. 한 줄에 한 bullet로 작성하세요. 반드시 아래 6개 항목 순서대로 작성:

• (주도 섹터 + 수요/공급 분석) 코스피를 이끄는 섹터(예: HBM·메모리 반도체, 조선, 방산, 2차전지)가 왜 강세인지 수요·공급 구조로 설명. 예: HBM3E 공급이 글로벌 수요를 못 따라가고 있다, 조선 수주잔고가 ○○년치를 넘었다 등 구체적 동인.

• (직접 수혜 기업 + 주가 전망) 그 섹터에서 직접 수혜받는 한국 기업 2~3개(예: 삼성전자, SK하이닉스, HD한국조선해양, 한화에어로스페이스) 실명. 각 기업의 향후 주가 방향성과 근거(실적 컨센서스·수주 잔고·점유율 등).

• (파생·연관 섹터) 반도체 투자 확대 → 전력·데이터센터·소부장·전선·변압기 등 파생 섹터의 수요 발생 메커니즘 설명.

• (파생 섹터 기업명 + 전망) 파생 섹터의 한국 상장 기업 2~3개(예: 한국전력, 두산에너빌리티, HD현대일렉트릭, LS일렉트릭, 한미반도체, 이수페타시스, 가온전선) 실명 거론. 각 기업 주가 전망 근거.

• (주요 계약·파트너십·실적) 뉴스 기반 또는 시장에 알려진 구체적 계약·MOU·실적 가이던스. 예: 두산에너빌리티-마이크로소프트 SMR 계약, 한미반도체-SK하이닉스 HBM 본더 장비 공급, 영업이익/매출 예상 수치 명시.

• (한국 정부·정치 영향 + 핵심 리스크) 산업통상자원부 K-반도체·K-방산 보조금, 미국 대중 규제 우회 부담, 원화 환율 수준, 국내 정치 이슈가 코스피에 미치는 영향. 가장 주의해야 할 리스크 1~2개 명시.
[/코스피전망]

모든 내용은 한국어로 작성하세요. 기업명·섹터명은 반드시 구체적으로 명시하세요."""

    try:
        client = Groq(api_key=groq_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.25,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return (
            f"[환율이유]AI 해설 오류: {e}[/환율이유]"
            "[금리이유][/금리이유][나스닥섹터][/나스닥섹터]"
            "[나스닥기업][/나스닥기업][나스닥전망][/나스닥전망]"
            "[코스피섹터][/코스피섹터][코스피기업][/코스피기업][코스피전망][/코스피전망]"
        )


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
        lines.append(f"\n🏦 *금리*\n{analysis['rate_reason'][:200]}")

    if analysis.get("nasdaq_sector"):
        bullets = [l.strip() for l in analysis["nasdaq_sector"].splitlines() if l.strip()][:2]
        lines.append("\n📈 *나스닥 주도 섹터*\n" + "\n".join(bullets))

    if analysis.get("nasdaq_outlook"):
        bullets = [l.strip() for l in analysis["nasdaq_outlook"].splitlines() if l.strip()][:2]
        lines.append("\n🔭 *나스닥 전망*\n" + "\n".join(bullets))

    if analysis.get("kospi_sector"):
        bullets = [l.strip() for l in analysis["kospi_sector"].splitlines() if l.strip()][:2]
        lines.append("\n📉 *코스피 주도 섹터*\n" + "\n".join(bullets))

    if analysis.get("kospi_outlook"):
        bullets = [l.strip() for l in analysis["kospi_outlook"].splitlines() if l.strip()][:2]
        lines.append("\n🇰🇷 *코스피 전망*\n" + "\n".join(bullets))

    return "\n".join(lines)


def render_html(date: str, hero_html: str, nasdaq_html: str, kospi_html: str) -> str:
    return HTML_TEMPLATE.format(
        date=date,
        hero_html=hero_html,
        nasdaq_html=nasdaq_html,
        kospi_html=kospi_html,
    )
