from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from cotton_dashboard.daily_article import _direction, _native_change, _topic_for, _weekly_rows
from cotton_dashboard.daily_cover import GREEN, HEIGHT, INK, LINE, MUTED, PAPER, RED, WIDTH, _font, _fit_font


@dataclass(frozen=True)
class WeeklyCover:
    title: str
    period: str
    path: Path


def generate_weekly_cover(payload: dict, output: Path, as_of: date | None = None) -> WeeklyCover:
    report_day = as_of or datetime.now(ZoneInfo("Asia/Shanghai")).date()
    week_end = report_day - timedelta(days=(report_day.weekday() - 4) % 7)
    week_start = week_end - timedelta(days=4)
    period = f"{week_start.month}月{week_start.day}日—{week_end.month}月{week_end.day}日"
    summaries = []
    for market, name in (("pakistan", "巴基斯坦"), ("india", "印度")):
        rows = _weekly_rows(payload["data"].get(market, []), week_start, week_end)
        if not rows:
            continue
        topic = _topic_for(market, rows)
        phrase = topic.phrase.replace("7日", "周内") if topic else "最新报价"
        summaries.append((name, phrase, _native_change(rows)))
    if not summaries:
        raise ValueError("上周巴基斯坦和印度均无可用数据")

    title = "上周棉价回顾"
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 18, HEIGHT), fill=RED)
    draw.text((54, 32), "全球棉价观察  ·  COTTON WEEKLY", font=_font(20, True), fill=INK)
    draw.line((54, 71, 846, 71), fill=INK, width=2)
    draw.text((54, 100), title, font=_fit_font(draw, title, 780, 62), fill=INK)
    draw.text((58, 180), f"{period}  ·  周度回顾", font=_font(24), fill=MUTED)
    draw.line((54, 225, 846, 225), fill=LINE, width=2)

    positions = (54, 450)
    for index, (name, phrase, change) in enumerate(summaries[:2]):
        x = positions[index]
        color = RED if change > 0 else GREEN
        draw.text((x, 247), name, font=_font(27, True), fill=INK)
        draw.text((x, 292), phrase, font=_fit_font(draw, phrase, 345, 30), fill=INK)
        change_text = f"周度{_direction(change)} {abs(change):.2f}%"
        draw.text((x, 337), change_text, font=_font(24, True), fill=color)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="JPEG", quality=92, optimize=True, progressive=False, subsampling=0)
    return WeeklyCover(title=title, period=period, path=output)
