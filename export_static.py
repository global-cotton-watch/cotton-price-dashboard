from __future__ import annotations

import shutil
from pathlib import Path

from cotton_dashboard.web import create_app

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "site"
STATIC = ROOT / "cotton_dashboard" / "static"


def export_site() -> Path:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    (OUTPUT / "static").mkdir(parents=True)
    (OUTPUT / "data").mkdir(parents=True)

    app = create_app()
    client = app.test_client()

    page = client.get("/")
    if page.status_code != 200:
        raise RuntimeError(f"首页导出失败：HTTP {page.status_code}")
    html = page.get_data(as_text=True)
    html = html.replace('href="/static/', 'href="./static/')
    html = html.replace('src="/static/', 'src="./static/')
    html = html.replace('content="http://localhost/static/', 'content="./static/')
    (OUTPUT / "index.html").write_text(html, encoding="utf-8")

    prices = client.get("/api/prices")
    if prices.status_code != 200:
        raise RuntimeError(f"价格JSON导出失败：HTTP {prices.status_code}")
    (OUTPUT / "data" / "prices.json").write_bytes(prices.data)

    shutil.copytree(STATIC, OUTPUT / "static", dirs_exist_ok=True)
    app_js = (STATIC / "app.js").read_text(encoding="utf-8")
    app_js = app_js.replace("fetch('/api/prices'", "fetch('./data/prices.json'")
    (OUTPUT / "static" / "app.js").write_text(app_js, encoding="utf-8")
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    output = export_site()
    print(f"GitHub Pages站点已导出：{output}")
