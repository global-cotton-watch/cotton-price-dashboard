from __future__ import annotations

import base64
import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

CHINA_URL = "https://www.cottonchina.org.cn/newprice/index.php"
CHINA_DATA_URL = "https://www.china-cotton.org/data"
CHINA_API_URL = "https://www.china-cotton.org/api/data/get_ccindex"
INVESTING_URL = "https://cn.investing.com/commodities/us-cotton-no.2-historical-data"
INVESTING_API_URL = "https://api.investing.com/api/financialdata/historical/8851"
INVESTING_READER_URL = f"https://r.jina.ai/{INVESTING_URL}"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/CT=F?range=1mo&interval=1d"
PAKISTAN_URL = "https://www.khistocks.com/commodity/karachi-cotton-rates.html"
INDIA_URL = "https://support.gujcot.com/desk/spot-rates"
INDIA_HISTORY_URL = "https://support.gujcot.com/desk/spot-rate-history"
FX_URL = "https://open.er-api.com/v6/latest/USD"
POUNDS_PER_TONNE = 2204.62262185
PAKISTAN_MAUND_KG = 37.324

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
}


class ScrapeError(RuntimeError):
    pass


def _number(value: str) -> float:
    match = re.search(r"-?[0-9][0-9,]*(?:\.[0-9]+)?", value)
    if not match:
        raise ScrapeError(f"找不到数值：{value!r}")
    return float(match.group(0).replace(",", ""))


def _fetched_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_fx_rates(session: requests.Session) -> dict[str, float | str]:
    response = session.get(FX_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("result") != "success":
        raise ScrapeError("汇率接口返回失败")
    rates = payload["rates"]
    required = ("CNY", "PKR", "INR")
    if any(code not in rates for code in required):
        raise ScrapeError("汇率接口缺少 CNY/PKR/INR")
    return {
        "date": datetime.fromtimestamp(payload["time_last_update_unix"], timezone.utc).date().isoformat(),
        "usd_cny": float(rates["CNY"]),
        "pkr_cny": float(rates["CNY"]) / float(rates["PKR"]),
        "inr_cny": float(rates["CNY"]) / float(rates["INR"]),
    }


def _china_api_headers() -> dict[str, str]:
    # These fragments and index encoding mirror the association data-center JS.
    # The legacy public page remains a fallback if its signing scheme changes.
    fragments_a = ["Hx", "EZK", "9nRSg", "myn8", "WdV", "W4k4", "w=="]
    fragments_b = ["==wVi", "Lp", "t7E", "a1C", "6AT", "q", "VHE", "GN", "GU"]
    indexes = (2, 5, 1, 4, 8)
    selected = [fragments_a[i] for i in indexes[:3]] + [fragments_b[i] for i in indexes[3:]]
    sign = hashlib.md5("".join(selected).encode()).hexdigest()
    binary_indexes = "-".join(format(i, "b") for i in indexes)
    signcode = base64.b64encode(binary_indexes.encode()).decode()
    return {
        **HEADERS,
        "sign": sign,
        "signcode": signcode,
        "systype": "mhxh",
        "Referer": CHINA_DATA_URL,
    }


def _china_point(
    day: str,
    value: float,
    change: float | None,
    source_name: str,
    source_url: str,
) -> dict:
    return {
        "market": "china", "date": day,
        "native_price": value, "native_unit": "CNY/吨", "cny_per_ton": value,
        "fx_rate": 1.0, "source_name": source_name,
        "source_url": source_url, "fetched_at": _fetched_at(),
        "metadata": {"grade": "CC Index 3128B", "change_cny": change},
    }


def _scrape_china_api(session: requests.Session) -> list[dict]:
    response = session.post(
        CHINA_API_URL,
        files={"type": (None, "nature"), "pageSize": (None, "10")},
        headers=_china_api_headers(),
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 1 or not payload.get("data"):
        raise ScrapeError(f"中国棉花协会API返回失败：{payload.get('msg', '无数据')}")
    points = []
    for row in payload["data"][:7]:
        day = str(row.get("date", ""))
        value = _number(str(row.get("data_3128", "")))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) or not 5000 <= value <= 50000:
            raise ScrapeError("中国3128B API返回了异常日期或价格")
        raw_change = row.get("data_3128_hb")
        change = _number(str(raw_change)) if raw_change not in (None, "", "-") else None
        points.append(_china_point(day, value, change, "中国棉花协会数据中心", CHINA_DATA_URL))
    return list(reversed(points))


def _scrape_china_legacy(session: requests.Session) -> list[dict]:
    response = session.get(CHINA_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "gb2312"
    soup = BeautifulSoup(response.text, "html.parser")
    target = None
    for table in soup.find_all("table"):
        cells = [c.get_text(" ", strip=True) for c in table.find_all(["th", "td"])]
        if "3128B" in cells and "2227B" in cells:
            target = table
            break
    if target is None:
        raise ScrapeError("中国棉花网页未找到3128B表格")
    now = datetime.now()
    points = []
    for row in target.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
        if len(cells) < 4 or not re.fullmatch(r"\d{2}/\d{2}", cells[0]):
            continue
        month, day = map(int, cells[0].split("/"))
        year = now.year - (1 if month > now.month + 2 else 0)
        value = _number(cells[1])
        points.append(_china_point(
            f"{year:04d}-{month:02d}-{day:02d}", value, None,
            "中国棉花信息网（协会API受限时备用）", CHINA_URL,
        ))
    if not points:
        raise ScrapeError("中国棉花网页未解析到价格")
    return points


def scrape_china(session: requests.Session, fx: dict) -> list[dict]:
    try:
        return _scrape_china_api(session)
    except (requests.RequestException, ValueError, KeyError, ScrapeError):
        return _scrape_china_legacy(session)


def _scrape_us_investing(session: requests.Session, fx: dict) -> list[dict]:
    params = {"start-date": "2020-01-01", "end-date": datetime.now().date().isoformat(), "interval": "P1D", "time-frame": "Daily"}
    headers = {**HEADERS, "Domain-Id": "cn", "Origin": "https://cn.investing.com", "Referer": INVESTING_URL}
    response = session.get(INVESTING_API_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    raw_rows = payload.get("data") or payload.get("rows") or []
    points = []
    for row in raw_rows[-14:]:
        date_value = row.get("direction_color") and row.get("rowDate") or row.get("date") or row.get("rowDateRaw")
        close = row.get("last_close") or row.get("close") or row.get("last")
        if date_value is None or close is None:
            continue
        if isinstance(date_value, (int, float)):
            day = datetime.fromtimestamp(date_value / (1000 if date_value > 10**11 else 1), timezone.utc).date().isoformat()
        else:
            day = datetime.fromisoformat(str(date_value)[:10]).date().isoformat()
        points.append(_us_point(day, float(str(close).replace(",", "")), fx, "Investing.com", INVESTING_URL, False))
    if not points:
        raise ScrapeError("Investing接口没有可解析数据")
    return points[-7:]


def _parse_investing_markdown(markdown: str, fx: dict) -> list[dict]:
    rows = []
    for line in markdown.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        match = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", cells[0])
        if not match:
            continue
        year, month, day = map(int, match.groups())
        close = _number(cells[1])
        rows.append(_us_point(
            f"{year:04d}-{month:02d}-{day:02d}", close, fx,
            "Investing.com（只读渲染）", INVESTING_URL, False,
        ))
    if not rows:
        raise ScrapeError("Investing只读页面没有可解析历史数据")
    rows.sort(key=lambda item: item["date"])
    return rows[-7:]


def _scrape_us_investing_reader(session: requests.Session, fx: dict) -> list[dict]:
    headers = dict(HEADERS)
    if token := os.environ.get("JINA_API_KEY"):
        headers["Authorization"] = f"Bearer {token}"
    response = session.get(INVESTING_READER_URL, headers=headers, timeout=60)
    response.raise_for_status()
    return _parse_investing_markdown(response.text, fx)


def _us_point(day: str, cents: float, fx: dict, source_name: str, source_url: str, fallback: bool) -> dict:
    cny_per_ton = cents / 100.0 * POUNDS_PER_TONNE * float(fx["usd_cny"])
    return {
        "market": "usa", "date": day, "native_price": cents,
        "native_unit": "美分/磅", "cny_per_ton": round(cny_per_ton, 2),
        "fx_rate": fx["usd_cny"], "source_name": source_name,
        "source_url": source_url, "fetched_at": _fetched_at(),
        "metadata": {
            "grade": "美国棉花2号", "fx_date": fx["date"],
            "fallback": fallback,
            "formula": "美分价/100 × 2204.6226 × USD/CNY",
        },
    }


def _scrape_us_yahoo(session: requests.Session, fx: dict) -> list[dict]:
    response = session.get(YAHOO_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    rows = []
    for stamp, close in zip(timestamps, closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
        rows.append(_us_point(day, round(float(close), 2), fx, "Yahoo Finance（Investing受限时备用）", YAHOO_URL, True))
    if not rows:
        raise ScrapeError("美棉备用接口没有数据")
    return rows[-7:]


def scrape_usa(session: requests.Session, fx: dict) -> list[dict]:
    try:
        return _scrape_us_investing(session, fx)
    except (requests.RequestException, ValueError, KeyError, ScrapeError):
        try:
            return _scrape_us_investing_reader(session, fx)
        except (requests.RequestException, ValueError, KeyError, ScrapeError):
            return _scrape_us_yahoo(session, fx)


def scrape_pakistan(session: requests.Session, fx: dict) -> list[dict]:
    page = session.get(PAKISTAN_URL, headers=HEADERS, timeout=30)
    page.raise_for_status()
    headers = {**HEADERS, "X-Requested-With": "XMLHttpRequest", "Referer": PAKISTAN_URL, "Origin": "https://www.khistocks.com"}
    payload = {
        "draw": "1", "start": "0", "length": "20", "search[value]": "", "search[regex]": "false",
        "order[0][column]": "0", "order[0][dir]": "desc", "id": "1", "from": "", "to": "",
    }
    for i, field in enumerate(("date", "date2", "exgin", "upcountry", "spot_rate")):
        payload.update({
            f"columns[{i}][data]": field, f"columns[{i}][name]": "",
            f"columns[{i}][searchable]": "true", f"columns[{i}][orderable]": "true" if i == 0 else "false",
            f"columns[{i}][search][value]": "", f"columns[{i}][search][regex]": "false",
        })
    response = session.post("https://www.khistocks.com/ajax/cotton_spot_rates", data=payload, headers=headers, timeout=30)
    response.raise_for_status()
    rows = response.json().get("data", [])[:7]
    if not rows:
        raise ScrapeError("巴基斯坦棉价接口没有数据")
    points = []
    for row in reversed(rows):
        ex_gin = _number(row["exgin"])
        cny_per_ton = ex_gin / PAKISTAN_MAUND_KG * 1000 * float(fx["pkr_cny"])
        points.append({
            "market": "pakistan", "date": row["date"], "native_price": ex_gin,
            "native_unit": "PKR/37.324kg", "cny_per_ton": round(cny_per_ton, 2),
            "fx_rate": fx["pkr_cny"], "source_name": "Khistocks Karachi Cotton Rates",
            "source_url": PAKISTAN_URL, "fetched_at": _fetched_at(),
            "metadata": {
                "grade": "Ex-Gin 出厂价", "fx_date": fx["date"],
                "upcountry_pkr": _number(row.get("upcountry", "0")),
                "spot_rate_pkr": _number(row.get("spot_rate", "0")),
                "formula": "Ex-Gin价 ÷ 37.324 × 1000 × PKR/CNY",
            },
        })
    return points


def _india_date(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"Date\s*:\s*(\d{2}-\d{2}-\d{4})", text)
    if not match:
        raise ScrapeError("印度页面未找到日期")
    return datetime.strptime(match.group(1), "%d-%m-%Y").date().isoformat()


def _parse_india_page(html: str, fx: dict, source_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    target = None
    for row in soup.select("table tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
        if cells and re.search(r"Shankar\s*-?\s*6", cells[0], re.I):
            target = cells
            break
    if target is None or len(target) < 9:
        raise ScrapeError("印度页面未找到Shankar 6价格")
    candy = _number(target[4])
    quintal = _number(target[6])
    cents_lb = _number(target[8])
    cny_per_ton = quintal * 10 * float(fx["inr_cny"])
    return {
        "market": "india", "date": _india_date(soup), "native_price": candy,
        "native_unit": "INR/Candy", "cny_per_ton": round(cny_per_ton, 2),
        "fx_rate": fx["inr_cny"], "source_name": "Gujcot Spot Rate",
        "source_url": source_url, "fetched_at": _fetched_at(),
        "metadata": {
            "grade": "Shankar 6 (S-6)", "rs_quintal": quintal,
            "cents_lb": cents_lb, "fx_date": fx["date"],
            "formula": "Rs/Quintal × 10 × INR/CNY",
        },
    }


def scrape_india(session: requests.Session, fx: dict) -> list[dict]:
    response = session.get(INDIA_HISTORY_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    urls = []
    for anchor in soup.select('table a[href*="spot-rates?date="]'):
        url = urljoin(INDIA_HISTORY_URL, anchor["href"])
        if url not in urls:
            urls.append(url)
        if len(urls) == 7:
            break
    if not urls:
        urls = [INDIA_URL]
    points = []
    for url in reversed(urls):
        page = session.get(url, headers=HEADERS, timeout=30)
        page.raise_for_status()
        points.append(_parse_india_page(page.text, fx, url))
    return points


SCRAPERS: dict[str, Callable[[requests.Session, dict], list[dict]]] = {
    "china": scrape_china,
    "usa": scrape_usa,
    "pakistan": scrape_pakistan,
    "india": scrape_india,
}
