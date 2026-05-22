import requests
import io
import csv
from datetime import datetime

TWELVE_DATA_BASE = "https://api.twelvedata.com/time_series"
FRED_FEDFUNDS_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS"


def _fetch_twelve(symbol: str, api_key: str) -> dict | None:
    if not api_key:
        print(f"[경고] {symbol}: TWELVE_DATA_API_KEY 미설정")
        return None
    try:
        params = {"symbol": symbol, "interval": "1day", "outputsize": 3, "apikey": api_key}
        resp = requests.get(TWELVE_DATA_BASE, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "error" or "values" not in data:
            print(f"[오류] {symbol}: {data.get('message', '알 수 없음')}")
            return None
        values = data["values"]  # 최신순 정렬
        if len(values) < 2:
            print(f"[경고] {symbol}: 데이터 부족 ({len(values)}행)")
            return None
        today_close = float(values[0]["close"])
        prev_close = float(values[1]["close"])
        change = today_close - prev_close
        change_pct = (change / prev_close) * 100
        print(f"[OK] {symbol}: {today_close:.2f} (전일比 {change:+.2f})")
        return {
            "value": round(today_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "date": values[0]["datetime"][:10],
        }
    except Exception as e:
        print(f"[오류] {symbol} 수집 실패: {e}")
        return None


def fetch_market_data(api_key: str) -> dict:
    return {
        "nasdaq": _fetch_twelve("IXIC", api_key),
        "usdkrw": _fetch_twelve("USD/KRW", api_key),
        "kospi": _fetch_twelve("KS11", api_key),
    }


def fetch_interest_rate() -> dict | None:
    try:
        resp = requests.get(FRED_FEDFUNDS_URL, timeout=15)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = [r for r in reader if r.get("FEDFUNDS") not in ("", ".")]
        if len(rows) < 2:
            print("[경고] FRED: 데이터 부족")
            return None
        latest = rows[-1]
        prev = rows[-2]
        value = float(latest["FEDFUNDS"])
        change = round(value - float(prev["FEDFUNDS"]), 2)
        print(f"[OK] 미국 기준금리: {value}% (전월比 {change:+.2f}%p, {latest['DATE']})")
        return {"value": value, "change": change, "date": latest["DATE"]}
    except Exception as e:
        print(f"[오류] FRED 기준금리 수집 실패: {e}")
        return None


def fetch_kor_rate(api_key: str) -> dict | None:
    if not api_key:
        print("[경고] 한국 기준금리: BOK_API_KEY 미설정")
        return None
    try:
        now = datetime.now()
        total = now.year * 12 + (now.month - 1) - 5
        from_year = total // 12
        from_month = total % 12 + 1
        from_ym = f"{from_year}{from_month:02d}"
        to_ym = f"{now.year}{now.month:02d}"
        url = (
            f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}"
            f"/json/kr/1/10/722Y001/M/{from_ym}/{to_ym}/0101000"
        )
        resp = requests.get(url, timeout=15)
        data = resp.json()
        rows = data.get("StatisticSearch", {}).get("row", [])
        rows = [r for r in rows if r.get("DATA_VALUE") not in ("", None)]
        if not rows:
            print("[경고] 한국 기준금리: 데이터 없음")
            return None
        latest = rows[-1]
        value = float(latest["DATA_VALUE"])
        change = round(value - float(rows[-2]["DATA_VALUE"]), 2) if len(rows) >= 2 else 0.0
        print(f"[OK] 한국 기준금리: {value}% (전월比 {change:+.2f}%p, {latest['TIME']})")
        return {
            "value": value,
            "change": change,
            "date": f"{latest['TIME'][:4]}년 {latest['TIME'][4:]}월",
        }
    except Exception as e:
        print(f"[오류] 한국 기준금리 수집 실패: {e}")
        return None
