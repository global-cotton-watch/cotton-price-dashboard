from __future__ import annotations

import argparse
import json
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from cotton_dashboard.daily_article import build_daily_email


def send(message_path: Path) -> str:
    payload = json.loads(message_path.read_text(encoding="utf-8"))
    article = build_daily_email(payload)
    username = os.environ["SMTP_USERNAME"]
    auth_code = os.environ["SMTP_AUTH_CODE"]
    recipient = os.environ.get("MAIL_TO", "gmw126@126.com")
    host = os.environ.get("SMTP_HOST", "smtp.126.com")
    port = int(os.environ.get("SMTP_PORT", "465"))

    message = EmailMessage()
    message["Subject"] = article.subject
    message["From"] = formataddr(("全球棉价观察", username))
    message["To"] = recipient
    message.set_content(article.plain)
    message.add_alternative(article.html, subtype="html")
    with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
        smtp.login(username, auth_code)
        smtp.send_message(message)
    return article.subject


def preview(message_path: Path, output: Path) -> str:
    article = build_daily_email(json.loads(message_path.read_text(encoding="utf-8")))
    output.mkdir(parents=True, exist_ok=True)
    (output / "subject.txt").write_text(article.subject, encoding="utf-8")
    (output / "article.txt").write_text(article.plain, encoding="utf-8")
    (output / "article.html").write_text(article.html, encoding="utf-8")
    return article.subject


def main() -> None:
    parser = argparse.ArgumentParser(description="生成或发送每日棉价公众号文章邮件")
    parser.add_argument("--data", type=Path, default=Path("site/data/prices.json"))
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    if args.preview:
        print(f"预览已生成：{preview(args.data, args.preview)}")
    if args.send:
        print(f"邮件已发送：{send(args.data)}")
    if not args.preview and not args.send:
        parser.error("至少指定 --preview 或 --send")


if __name__ == "__main__":
    main()
