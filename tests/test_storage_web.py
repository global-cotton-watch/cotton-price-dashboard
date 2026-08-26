from cotton_dashboard.storage import PriceStore
from cotton_dashboard.web import create_app


def point(day, value):
    return {
        "market": "china", "date": day, "native_price": value,
        "native_unit": "CNY/吨", "cny_per_ton": value, "fx_rate": 1,
        "source_name": "test", "source_url": "https://example.com",
        "fetched_at": "2026-08-26T00:00:00+00:00", "metadata": {"grade": "3128B"},
    }


def test_store_keeps_latest_seven_in_chronological_order(tmp_path):
    store = PriceStore(tmp_path / "test.db")
    store.upsert(point(f"2026-08-{day:02d}", 18000 + day) for day in range(1, 10))
    rows = store.latest_by_market()["china"]
    assert len(rows) == 7
    assert rows[0]["date"] == "2026-08-03"
    assert rows[-1]["date"] == "2026-08-09"


def test_prices_api(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "api.db")})
    app.extensions["price_store"].upsert([point("2026-08-26", 18191)])
    response = app.test_client().get("/api/prices")
    assert response.status_code == 200
    assert response.json["data"]["china"][0]["cny_per_ton"] == 18191
    assert response.json["markets"]["usa"]["grade"] == "2号棉花"
