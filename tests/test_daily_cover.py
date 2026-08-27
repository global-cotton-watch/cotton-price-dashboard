import json

from email_daily_update import compose_message, preview, send
from PIL import Image

from cotton_dashboard.daily_article import build_daily_email
from cotton_dashboard.daily_cover import generate_daily_cover


def market(name, native_values, cny_values, unit):
    return [
        {
            "market": name,
            "date": f"2026-08-{20 + index:02d}",
            "native_price": native,
            "native_unit": unit,
            "cny_per_ton": cny,
            "source_name": "test",
        }
        for index, (native, cny) in enumerate(zip(native_values, cny_values))
    ]


def payload():
    return {
        "data": {
            "china": market("china", [18000, 18100], [18000, 18100], "CNY/吨"),
            "usa": market("usa", [65, 66], [14000, 14200], "美分/磅"),
            "pakistan": market(
                "pakistan",
                [18000, 18500, 19300, 18800],
                [12000, 12400, 13000, 12600],
                "PKR/37.324kg",
            ),
            "india": market(
                "india",
                [68000, 68100, 68200, 68250],
                [13700, 13720, 13740, 13750],
                "INR/Candy",
            ),
        },
        "disclaimer": "价格仅供参考。",
    }


def test_generates_wechat_article_cover(tmp_path):
    result = generate_daily_cover(payload(), tmp_path / "daily-cover.jpg")
    assert result.title == "巴基斯坦棉花高位回落"
    assert result.path.exists()
    with Image.open(result.path) as image:
        assert image.format == "JPEG"
        assert image.size == (900, 383)
        assert image.mode == "RGB"
        assert image.getbbox() == (0, 0, 900, 383)


def test_email_contains_cover_as_downloadable_attachment(tmp_path):
    image = generate_daily_cover(payload(), tmp_path / "daily-cover.jpg")
    article = build_daily_email(payload())
    message = compose_message(
        article,
        "sender@example.com",
        "recipient@example.com",
        image.path.read_bytes(),
    )
    image_parts = [part for part in message.walk() if part.get_content_type() == "image/jpeg"]
    assert len(image_parts) == 1
    assert image_parts[0]["Content-ID"] is None
    assert image_parts[0].get_content_disposition() == "attachment"
    assert image_parts[0].get_filename() == "每日棉价封面.jpg"
    html = next(part for part in message.walk() if part.get_content_type() == "text/html")
    assert "cid:" not in html.get_content()
    assert "点击底部「阅读原文」浏览详细内容" in html.get_content()


def test_send_delivers_generated_cover_attachment(tmp_path, monkeypatch):
    data_path = tmp_path / "prices.json"
    data_path.write_text(json.dumps(payload()), encoding="utf-8")
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
    send(data_path)
    assert len(delivered) == 1
    assert any(part.get_content_type() == "image/jpeg" for part in delivered[0].walk())


def test_preview_writes_ready_to_upload_cover(tmp_path):
    data_path = tmp_path / "prices.json"
    data_path.write_text(json.dumps(payload()), encoding="utf-8")
    output = tmp_path / "preview"
    preview(data_path, output)
    assert (output / "每日棉价封面.jpg").exists()
    assert "点击底部「阅读原文」浏览详细内容" in (output / "article.html").read_text(encoding="utf-8")
