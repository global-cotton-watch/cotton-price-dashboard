from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from cotton_dashboard.daily_article import _direction, _select_topic

WIDTH = 900
HEIGHT = 383
PAPER = "#f4efe5"
INK = "#1d2925"
MUTED = "#6f7872"
GREEN = "#1c7057"
RED = "#bd493f"
LINE = "#d9d2c5"


@dataclass(frozen=True)
class DailyCover:
    title: str
    path: Path


def _font_path(bold: bool = False) -> str:
    configured = os.environ.get("COTTON_FONT_BOLD" if bold else "COTTON_FONT")
    candidates = [
        configured,
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError("未找到可用字体；Linux请安装 fonts-noto-cjk")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_font_path(bold), size)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int) -> ImageFont.FreeTypeFont:
    while size > 30:
        font = _font(size, True)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 2
    return _font(size, True)


def _draw_trend(draw: ImageDraw.ImageDraw, rows: list[dict], color: str) -> None:
    values = [row["native_price"] for row in rows]
    low, high = min(values), max(values)
    span = max(high - low, 1)
    left, top, right, bottom = 620, 110, 854, 300
    points = []
    for index, value in enumerate(values):
        x = (left + right) / 2 if len(values) == 1 else left + index * (right - left) / (len(values) - 1)
        y = top + (high - value) / span * (bottom - top)
        points.append((x, y))
    if len(points) > 1:
        draw.line(points, fill=color, width=8, joint="curve")
    for x, y in points:
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=PAPER, outline=color, width=4)


def generate_daily_cover(payload: dict, output: Path) -> DailyCover:
    topic = _select_topic(payload["data"])
    rows = payload["data"][topic.market]
    latest = rows[-1]
    market_name = "巴基斯坦" if topic.market == "pakistan" else "印度"
    title = f"{market_name}棉花{topic.phrase}"
    accent = RED if topic.daily_change > 0 else GREEN

    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 18, HEIGHT), fill=accent)
    draw.text((54, 36), "全球棉价观察  ·  COTTON MARKET PULSE", font=_font(20, True), fill=INK)
    draw.line((54, 75, 846, 75), fill=INK, width=2)
    draw.text((54, 112), title, font=_fit_font(draw, title, 535, 62), fill=INK)
    draw.text((58, 211), f"{latest['date']}  ·  每日主题", font=_font(24), fill=MUTED)
    price = f"昨日 {latest['native_price']:,.0f} {latest.get('native_unit', '')}"
    draw.text((58, 264), price, font=_fit_font(draw, price, 530, 31), fill=INK)
    change = f"{_direction(topic.daily_change)} {abs(topic.daily_change):.2f}%"
    draw.text((58, 316), change, font=_font(25, True), fill=accent)
    _draw_trend(draw, rows, accent)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="JPEG", quality=92, optimize=True, progressive=False, subsampling=0)
    return DailyCover(title=title, path=output)
