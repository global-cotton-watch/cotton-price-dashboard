from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template

from .service import update_all
from .storage import PriceStore

MARKETS = {
    "china": {"name": "中国棉花", "short": "中国", "grade": "3128B", "color": "#d94f3d"},
    "usa": {"name": "美国棉花", "short": "美国", "grade": "2号棉花", "color": "#3268c7"},
    "pakistan": {"name": "巴基斯坦棉花", "short": "巴基斯坦", "grade": "Ex-Gin", "color": "#27956f"},
    "india": {"name": "印度棉花", "short": "印度", "grade": "Shankar 6", "color": "#d98a27"},
}


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    default_db = Path(app.root_path).parent / "data" / "cotton.db"
    app.config.from_mapping(DATABASE=os.environ.get("COTTON_DATABASE", str(default_db)))
    if test_config:
        app.config.update(test_config)
    store = PriceStore(app.config["DATABASE"])
    app.extensions["price_store"] = store

    @app.get("/")
    def index():
        return render_template("index.html", markets=MARKETS)

    @app.get("/api/prices")
    def prices():
        data = store.latest_by_market(limit=7)
        return jsonify({
            "markets": MARKETS,
            "data": data,
            "updated_at": store.latest_fetch_time(),
            "disclaimer": "价格仅供市场参考，不构成交易建议；人民币折算未含关税、增值税、保险、港杂费等。",
        })

    @app.post("/api/update")
    def update():
        token = os.environ.get("UPDATE_TOKEN")
        from flask import request
        if token and request.headers.get("X-Update-Token") != token:
            return jsonify({"error": "unauthorized"}), 401
        result = update_all(store)
        return jsonify(result), 200 if result["status"] in {"success", "partial"} else 502

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "updated_at": store.latest_fetch_time()})

    return app
