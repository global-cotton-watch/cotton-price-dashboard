import pytest

from cotton_dashboard.scrapers import (
    _china_api_headers,
    _parse_india_page,
    _parse_investing_markdown,
    _us_point,
)

FX = {"date": "2026-08-26", "usd_cny": 7.0, "pkr_cny": 0.025, "inr_cny": 0.08}


def test_us_landed_conversion_adds_ten_cents():
    point = _us_point("2026-08-25", 70.0, FX, "test", "https://example.com", False)
    assert point["metadata"]["landed_cents_lb"] == 80.0
    assert point["cny_per_ton"] == pytest.approx(0.8 * 2204.62262185 * 7.0, abs=0.01)


def test_china_api_signature_matches_official_frontend_scheme():
    headers = _china_api_headers()
    assert headers["sign"] == "3d6be1ff7e72acfb14a4d3ef1071a9c9"
    assert headers["signcode"] == "MTAtMTAxLTEtMTAwLTEwMDA="


def test_investing_markdown_parser_returns_chronological_latest_seven():
    markdown = "\n".join(
        f"| 2026年08月{day:02d}日 | {80 + day / 10:.2f} | 80.00 | 81.00 | 79.00 | 1 | 0% |"
        for day in range(26, 17, -1)
    )
    rows = _parse_investing_markdown(markdown, FX)
    assert len(rows) == 7
    assert rows[0]["date"] == "2026-08-20"
    assert rows[-1]["date"] == "2026-08-26"
    assert rows[-1]["native_price"] == 82.6


def test_india_shankar_6_parser_uses_quintal_for_conversion():
    html = """
    <html><body><div>Date : 25-08-2026</div><table>
    <tr><td>Shankar 6</td><td>29</td><td>3.8</td><td>68,900 - 69,200</td>
    <td>69,050</td><td>▼ 150</td><td>19,417</td><td>▼ 42</td><td>92.31</td><td>▼ 0.20</td></tr>
    </table></body></html>
    """
    point = _parse_india_page(html, FX, "https://example.com")
    assert point["date"] == "2026-08-25"
    assert point["native_price"] == 69050
    assert point["metadata"]["rs_quintal"] == 19417
    assert point["cny_per_ton"] == pytest.approx(15533.6)
