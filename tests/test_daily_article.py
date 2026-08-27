from cotton_dashboard.daily_article import SITE_URL, build_daily_email


def rows(market, start, end, native, unit):
    common = {"market": market, "native_unit": unit, "source_name": "test"}
    return [
        {**common, "date": "2026-08-18", "native_price": start, "cny_per_ton": start},
        {**common, "date": "2026-08-26", "native_price": native, "cny_per_ton": end},
    ]


def trend_rows(market, cny_values, native_values, unit):
    return [
        {
            "market": market,
            "date": f"2026-08-{20 + index:02d}",
            "native_price": native,
            "native_unit": unit,
            "cny_per_ton": cny,
        }
        for index, (cny, native) in enumerate(zip(cny_values, native_values))
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


def test_pakistan_high_pullback_drives_subject():
    data = payload()
    data["data"]["pakistan"] = trend_rows(
        "pakistan", [12000, 12400, 13000, 12600], [18000, 18500, 19300, 18800], "PKR/37.324kg"
    )
    data["data"]["india"] = trend_rows(
        "india", [13700, 13720, 13740, 13750], [68000, 68100, 68200, 68250], "INR/Candy"
    )
    article = build_daily_email(data)
    assert article.subject == "巴基斯坦棉花高位回落｜昨日18,800 PKR/37.324kg"
    assert "本期主题：巴基斯坦棉花高位回落" in article.plain
    assert "18,800.00 PKR/37.324kg" in article.plain
    assert SITE_URL in article.plain
    assert "四国最新报价" in article.html


def test_india_low_rebound_drives_subject():
    data = payload()
    data["data"]["pakistan"] = trend_rows(
        "pakistan", [12000, 12020, 12030, 12040], [18000, 18020, 18030, 18040], "PKR/37.324kg"
    )
    data["data"]["india"] = trend_rows(
        "india", [14000, 13200, 12800, 13300], [70000, 66000, 64000, 66500], "INR/Candy"
    )
    article = build_daily_email(data)
    assert article.subject == "印度棉花低位反弹｜昨日66,500 INR/Candy"


def test_topic_uses_native_market_prices_not_fx_conversion():
    data = payload()
    data["data"]["pakistan"] = trend_rows(
        "pakistan", [12000, 12100, 12200], [18000, 19000, 18500], "PKR/37.324kg"
    )
    data["data"]["india"] = trend_rows(
        "india", [13700, 13710, 13720], [68000, 68010, 68020], "INR/Candy"
    )
    article = build_daily_email(data)
    assert article.subject == "巴基斯坦棉花高位回落｜昨日18,500 PKR/37.324kg"


def test_missing_one_focus_market_uses_available_market():
    data = payload()
    data["data"]["pakistan"] = []
    article = build_daily_email(data)
    assert article.subject.startswith("印度棉花")


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
