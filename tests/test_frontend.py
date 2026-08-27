import json
import subprocess
from pathlib import Path


def test_chart_svg_has_y_axis_labels():
    app_js = Path("cotton_dashboard/static/app.js").read_text(encoding="utf-8")
    chart_code = app_js[:app_js.index("function renderMarket")]
    rows = [
        {"cny_per_ton": 12000},
        {"cny_per_ton": 12400},
        {"cny_per_ton": 13000},
        {"cny_per_ton": 12600},
    ]
    assertion = f"""
const svg = chartSvg({json.dumps(rows)}, '#27956f');
if ((svg.match(/class=\"y-axis-label\"/g) || []).length !== 3) throw new Error('expected three y-axis labels');
if (!svg.includes('class=\"axis-unit\"') || !svg.includes('元/吨')) throw new Error('expected y-axis unit');
if (svg.includes('x1=\"0\"')) throw new Error('grid must leave room for y-axis');
"""
    result = subprocess.run(
        ["node", "-e", chart_code + assertion],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr