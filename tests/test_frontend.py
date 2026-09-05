import json
import subprocess
from pathlib import Path


def test_chart_svg_uses_native_prices_and_market_unit():
    app_js = Path("cotton_dashboard/static/app.js").read_text(encoding="utf-8")
    chart_code = app_js[:app_js.index("function renderMarket")]
    rows = [
        {"native_price": 90.12, "cny_per_ton": 12000},
        {"native_price": 91.34, "cny_per_ton": 12400},
        {"native_price": 92.56, "cny_per_ton": 13000},
        {"native_price": 91.78, "cny_per_ton": 12600},
    ]
    assertion = f"""
const svg = chartSvg({json.dumps(rows)}, '#27956f', '美分/磅');
if ((svg.match(/class=\"y-axis-label\"/g) || []).length !== 3) throw new Error('expected three y-axis labels');
if (!svg.includes('class=\"axis-unit\"') || !svg.includes('美分/磅')) throw new Error('expected native y-axis unit');
if (!svg.includes('92.56') || !svg.includes('90.12')) throw new Error('expected native price ticks');
if (svg.includes('13,000') || svg.includes('12,000')) throw new Error('must not chart CNY prices');
if (svg.includes('x1=\"0\"')) throw new Error('grid must leave room for y-axis');
"""
    result = subprocess.run(
        ["node", "-e", chart_code + assertion],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_usa_copy_describes_direct_quote_conversion_without_premium():
    app_js = Path("cotton_dashboard/static/app.js").read_text(encoding="utf-8")
    index_html = Path("cotton_dashboard/templates/index.html").read_text(encoding="utf-8")
    combined = app_js + index_html
    assert "加10美分" not in combined
    assert "报价+10" not in combined
    assert "美分/磅收盘价直接折算" in index_html
    assert "报价 ÷ 100 × 2204.6226 × USD/CNY" in index_html


def test_website_hides_cotton_quote_sources():
    app_js = Path("cotton_dashboard/static/app.js").read_text(encoding="utf-8")
    index_html = Path("cotton_dashboard/templates/index.html").read_text(encoding="utf-8")
    assert "source_name" not in app_js
    assert "source_url" not in app_js
    assert "备用行情源" not in app_js
    assert "原始报价来自各市场网站" not in index_html