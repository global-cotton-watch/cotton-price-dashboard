import json
from datetime import date

from cotton_dashboard.daily_article import build_weekly_email
from email_daily_update import build_report, compose_message, send


def weekly_rows(market, values, cny_values, unit):
    return [
        {
            "market": market,
            "date": f"2026-08-{24 + index:02d}",
            "native_price": value,
            "native_unit": unit,
            "cny_per_ton": cny,
        }
        for index, (value, cny) in enumerate(zip(values, cny_values))
    ]


def test_weekly_report_summarizes_pakistan_and_india_only():
    payload = {
        "data": {
            "china": weekly_rows("china", [18000, 18100], [18000, 18100], "CNY/吨"),
            "usa": weekly_rows("usa", [90, 91], [13000, 13200], "美分/磅"),
            "pakistan": weekly_rows(
                "pakistan",
                [18000, 18200, 18500, 19000, 18800],
                [11800, 11900, 12100, 12400, 12200],
                "PKR/37.324kg",
            ),
            "india": weekly_rows(
                "india",
                [68000, 67900, 68100, 68050, 68200],
                [13500, 13480, 13520, 13510, 13540],
                "INR/Candy",
            ),
        },
        "disclaimer": "价格仅供参考。",
    }
    article = build_weekly_email(payload, as_of=date(2026, 8, 29))
    assert article.subject == "上周棉价回顾｜巴基斯坦高位回落，印度升至周内高位"
    assert "统计区间：8月24日—8月28日" in article.plain
    assert "巴基斯坦" in article.html
    assert "印度" in article.html
    assert "中国3128B" not in article.html
    assert "美国2号棉花" not in article.html
    assert "周涨跌：上涨 4.44%" in article.plain
    assert "周涨跌：上涨 0.29%" in article.plain
    assert "点击底部「阅读原文」浏览详细内容" in article.html


def test_email_builder_selects_weekly_report():
    payload = {
        "data": {
            "pakistan": weekly_rows("pakistan", [18000, 18800], [11800, 12200], "PKR/37.324kg"),
            "india": weekly_rows("india", [68000, 68200], [13500, 13540], "INR/Candy"),
        }
    }
    article = build_report(payload, "weekly", as_of=date(2026, 8, 29))
    assert article.subject.startswith("上周棉价回顾｜")


def test_weekly_email_does_not_attach_a_daily_cover():
    payload = {
        "data": {
            "pakistan": weekly_rows("pakistan", [18000, 18800], [11800, 12200], "PKR/37.324kg"),
            "india": weekly_rows("india", [68000, 68200], [13500, 13540], "INR/Candy"),
        }
    }
    article = build_report(payload, "weekly", as_of=date(2026, 8, 29))
    message = compose_message(article, "sender@example.com", "recipient@example.com", None)
    assert not any(part.get_content_maintype() == "image" for part in message.walk())


def test_send_delivers_weekly_report_without_daily_cover(tmp_path, monkeypatch):
    payload = {
        "data": {
            "pakistan": weekly_rows("pakistan", [18000, 18800], [11800, 12200], "PKR/37.324kg"),
            "india": weekly_rows("india", [68000, 68200], [13500, 13540], "INR/Candy"),
        }
    }
    data_path = tmp_path / "prices.json"
    data_path.write_text(json.dumps(payload), encoding="utf-8")
    delivered = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, username, auth_code):
            pass

        def send_message(self, message):
            delivered.append(message)

    monkeypatch.setenv("SMTP_USERNAME", "sender@example.com")
    monkeypatch.setenv("SMTP_AUTH_CODE", "test-code")
    monkeypatch.setenv("MAIL_TO", "recipient@example.com")
    monkeypatch.setattr("email_daily_update.smtplib.SMTP_SSL", FakeSMTP)
    send(data_path, report_type="weekly", as_of=date(2026, 8, 29))
    assert delivered[0]["Subject"].startswith("上周棉价回顾｜")
    assert not any(part.get_content_maintype() == "image" for part in delivered[0].walk())
