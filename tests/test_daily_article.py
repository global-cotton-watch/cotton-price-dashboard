from cotton_dashboard.daily_article import SITE_URL, build_daily_email


def rows(market, start, end, native, unit):
    common = {"market": market, "native_unit": unit, "source_name": "test"}
    return [
        {**common, "date": "2026-08-18", "native_price": start, "cny_per_ton": start},
        {**common, "date": "2026-08-26", "native_price": native, "cny_per_ton": end},
    ]


def payload(pakistan_end=10100, india_end=20200):
    return {
        "data": {
            "china": rows("china", 18000, 18100, 18100, "CNY/吨"),
            "usa": rows("usa", 14000, 14100, 64.5, "美分/磅"),
            "pakistan": rows("pakistan", 10000, pakistan_end, 16800, "PKR/37.324kg"),
            "india": rows("india", 20000, india_end, 55800, "Rs./Candy"),
        },
        "disclaimer": "价格仅供参考。",
    }


def test_subject_uses_pakistan_and_india_latest_prices():
    article = build_daily_email(payload(pakistan_end=10500, india_end=20200))
    assert article.subject == "巴基斯坦/印度棉花昨日价格｜16,800 PKR/37.324kg / 55,800 Rs./Candy"
    assert "16,800.00 PKR/37.324kg" in article.plain
    assert "55,800.00 Rs./Candy" in article.plain
    assert "2026-08-26" in article.plain
    assert SITE_URL in article.plain
    assert "四国最新报价" in article.html


def test_missing_one_focus_market_is_shown_as_unavailable():
    data = payload()
    data["data"]["pakistan"] = []
    article = build_daily_email(data)
    assert "巴基斯坦/印度棉花昨日价格｜暂无报价 / 55,800 Rs./Candy" == article.subject
    assert "巴基斯坦Ex-Gin：暂无报价" in article.plain


def test_missing_focus_markets_is_rejected():
    data = payload()
    data["data"]["pakistan"] = []
    data["data"]["india"] = []
    try:
        build_daily_email(data)
    except ValueError as exc:
        assert "无可用数据" in str(exc)
    else:
        raise AssertionError("expected ValueError")
