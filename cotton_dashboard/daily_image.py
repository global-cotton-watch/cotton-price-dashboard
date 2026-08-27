from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from cotton_dashboard.daily_article import LABELS, SITE_URL, _change, _direction, _select_topic

WIDTH = 900
HEIGHT = 1500
PAPER = "#f4efe5"
CARD = "#fffdf7"
INK = "#1d2925"
MUTED = "#6f7872"
GREEN = "#1c7057"
RED = "#bd493f"
LINE = "#d9d2c5"


@dataclass(frozen=True)
class DailyImage:
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


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    while size > 22:
        font = _font(size, bold)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 2
    return _font(size, bold)


def _draw_trend(draw: ImageDraw.ImageDraw, rows: list[dict], box: tuple[int, int, int, int], color: str) -> None:
    left, top, right, bottom = box
    values = [row["native_price"] for row in rows]
    low, high = min(values), max(values)
    span = max(high - low, 1)
    for index in range(3):
        y = top + index * (bottom - top) / 2
        draw.line((left, y, right, y), fill=LINE, width=2)
    points = []
    for index, value in enumerate(values):
        x = (left + right) / 2 if len(values) == 1 else left + index * (right - left) / (len(values) - 1)
        y = top + (high - value) / span * (bottom - top)
        points.append((x, y))
    if len(points) > 1:
        draw.line(points, fill=color, width=6, joint="curve")
    for x, y in points:
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=CARD, outline=color, width=4)


def generate_daily_image(payload: dict, output: Path) -> DailyImage:
    data = payload["data"]
    topic = _select_topic(data)
    focus_rows = data[topic.market]
    latest = focus_rows[-1]
    market_name = "巴基斯坦" if topic.market == "pakistan" else "印度"
    title = f"{market_name}棉花{topic.phrase}"
    accent = RED if topic.daily_change > 0 else GREEN

    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    draw.text((56, 48), "全球棉价观察  ·  COTTON MARKET PULSE", font=_font(23, True), fill=INK)
    draw.line((56, 88, 844, 88), fill=INK, width=2)
    draw.text((56, 130), title, font=_fit_font(draw, title, 788, 72, True), fill=INK)
    draw.text((56, 235), f"{latest['date']}  ·  每日主题", font=_font(25), fill=MUTED)

    draw.rounded_rectangle((48, 300, 852, 690), radius=24, fill=CARD, outline=LINE, width=2)
    draw.rectangle((48, 300, 62, 690), fill=accent)
    draw.text((86, 338), "昨日价格", font=_font(27, True), fill=MUTED)
    value = f"{latest['native_price']:,.0f}"
    draw.text((86, 385), value, font=_fit_font(draw, value, 480, 76, True), fill=INK)
    draw.text((90, 478), latest.get("native_unit", ""), font=_font(27), fill=MUTED)
    direction = _direction(topic.daily_change)
    draw.text((580, 404), f"{direction} {abs(topic.daily_change):.2f}%", font=_font(31, True), fill=accent)
    draw.text((580, 455), "较上一交易日", font=_font(22), fill=MUTED)
    draw.text((86, 525), "最近报价走势", font=_font(22, True), fill=INK)
    _draw_trend(draw, focus_rows, (90, 570, 810, 650), accent)

    draw.text((48, 748), "四国最新报价", font=_font(38, True), fill=INK)
    draw.text((48, 802), "人民币参考价 · 元/吨", font=_font(22), fill=MUTED)
    positions = [(48, 850), (460, 850), (48, 1065), (460, 1065)]
    for key, (x, y) in zip(("china", "usa", "pakistan", "india"), positions):
        rows = data.get(key, [])
        draw.rounded_rectangle((x, y, x + 392, y + 185), radius=18, fill=CARD, outline=LINE, width=2)
        draw.text((x + 24, y + 21), LABELS[key], font=_font(25, True), fill=INK)
        if not rows:
            draw.text((x + 24, y + 82), "暂无报价", font=_font(29), fill=MUTED)
            continue
        row = rows[-1]
        draw.text((x + 24, y + 70), f"¥ {row['cny_per_ton']:,.0f}", font=_font(39, True), fill=INK)
        native = f"{row['native_price']:,.0f} {row.get('native_unit', '')}".strip()
        draw.text((x + 24, y + 128), native, font=_fit_font(draw, native, 344, 21), fill=MUTED)

    draw.line((48, 1305, 852, 1305), fill=INK, width=2)
    draw.text((48, 1340), "完整7日走势与数据来源", font=_font(25, True), fill=INK)
    draw.text((48, 1382), SITE_URL, font=_fit_font(draw, SITE_URL, 804, 22), fill=GREEN)
    draw.text((48, 1432), "休市日使用最近一个有报价的交易日 · 价格仅供市场参考", font=_font(20), fill=MUTED)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)
    return DailyImage(title=title, path=output)
