from __future__ import annotations

import argparse
import json
import os
import smtplib
import tempfile
from datetime import date
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from cotton_dashboard.daily_article import build_daily_email, build_weekly_email
from cotton_dashboard.daily_cover import generate_daily_cover


def build_report(payload: dict, report_type: str, as_of: date | None = None):
    if report_type == "daily":
        return build_daily_email(payload, as_of=as_of)
    if report_type == "weekly":
        return build_weekly_email(payload, as_of=as_of)
    raise ValueError(f"未知报告类型：{report_type}")


def compose_message(article, sender: str, recipient: str, image_bytes: bytes | None) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = article.subject
    message["From"] = formataddr(("全球棉价观察", sender))
    message["To"] = recipient
    message.set_content(article.plain)
    message.add_alternative(article.html, subtype="html")
    if image_bytes is not None:
        message.add_attachment(
            image_bytes,
            maintype="image",
            subtype="jpeg",
            filename="每日棉价封面.jpg",
        )
    return message


def send(message_path: Path, report_type: str = "daily", as_of: date | None = None) -> str:
    payload = json.loads(message_path.read_text(encoding="utf-8"))
    article = build_report(payload, report_type, as_of=as_of)
    username = os.environ["SMTP_USERNAME"]
    auth_code = os.environ["SMTP_AUTH_CODE"]
    recipient = os.environ.get("MAIL_TO", "gmw126@126.com")
    host = os.environ.get("SMTP_HOST", "smtp.126.com")
    port = int(os.environ.get("SMTP_PORT", "465"))

    with tempfile.TemporaryDirectory(prefix="cotton-daily-") as temp_dir:
        image_bytes = None
        if report_type == "daily":
            image = generate_daily_cover(payload, Path(temp_dir) / "每日棉价封面.jpg", as_of=as_of)
            image_bytes = image.path.read_bytes()
        message = compose_message(article, username, recipient, image_bytes)
        with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
            smtp.login(username, auth_code)
            smtp.send_message(message)
    return article.subject


def preview(message_path: Path, output: Path, report_type: str = "daily", as_of: date | None = None) -> str:
    payload = json.loads(message_path.read_text(encoding="utf-8"))
    article = build_report(payload, report_type, as_of=as_of)
    output.mkdir(parents=True, exist_ok=True)
    if report_type == "daily":
        generate_daily_cover(payload, output / "每日棉价封面.jpg", as_of=as_of)
    (output / "subject.txt").write_text(article.subject, encoding="utf-8")
    (output / "article.txt").write_text(article.plain, encoding="utf-8")
    (output / "article.html").write_text(article.html, encoding="utf-8")
    return article.subject


def main() -> None:
    parser = argparse.ArgumentParser(description="生成或发送每日棉价公众号文章邮件")
    parser.add_argument("--data", type=Path, default=Path("site/data/prices.json"))
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--report-type", choices=("daily", "weekly"), default="daily")
    args = parser.parse_args()
    if args.preview:
        print(f"预览已生成：{preview(args.data, args.preview, args.report_type)}")
    if args.send:
        print(f"邮件已发送：{send(args.data, args.report_type)}")
    if not args.preview and not args.send:
        parser.error("至少指定 --preview 或 --send")


if __name__ == "__main__":
    main()
