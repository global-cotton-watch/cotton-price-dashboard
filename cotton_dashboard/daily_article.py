from __future__ import annotations

from dataclasses import dataclass
from html import escape

SITE_URL = "https://global-cotton-watch.github.io/cotton-price-dashboard/"
LABELS = {
    "china": "中国3128B",
    "usa": "美国2号棉花",
    "pakistan": "巴基斯坦Ex-Gin",
    "india": "印度Shankar 6",
}


@dataclass(frozen=True)
class DailyEmail:
    subject: str
    plain: str
    html: str


@dataclass(frozen=True)
class Topic:
    market: str
    phrase: str
    score: float
    daily_change: float


def _change(rows: list[dict]) -> float:
    if len(rows) < 2 or not rows[0].get("cny_per_ton"):
        return 0.0
    return (rows[-1]["cny_per_ton"] / rows[0]["cny_per_ton"] - 1) * 100


def _direction(value: float) -> str:
    if value > 0.005:
        return "上涨"
    if value < -0.005:
        return "下跌"
    return "持平"


def _price(row: dict) -> str:
    value = row.get("native_price")
    return "暂无" if value is None else f"{value:,.2f} {row.get('native_unit', '')}".strip()


def _headline_price(rows: list[dict]) -> str:
    latest = rows[-1]
    return f"{latest['native_price']:,.0f} {latest.get('native_unit', '')}".strip()


def _topic_for(market: str, rows: list[dict]) -> Topic | None:
    if not rows:
        return None
    values = [row["native_price"] for row in rows]
    if len(values) < 2 or not values[-2]:
        return Topic(market, "最新报价", 0.0, 0.0)
    previous, current = values[-2:]
    daily = (current / previous - 1) * 100
    span = max(values) - min(values)
    high = max(values) - span * 0.15
    low = min(values) + span * 0.15
    if len(values) >= 3 and daily < -0.005 and previous >= high:
        phrase, bonus = "高位回落", 2.0
    elif len(values) >= 3 and daily > 0.005 and previous <= low:
        phrase, bonus = "低位反弹", 2.0
    elif daily > 0.005 and current == max(values):
        phrase, bonus = "升至7日高位", 1.0
    elif daily < -0.005 and current == min(values):
        phrase, bonus = "降至7日低位", 1.0
    elif len(values) >= 3 and values[-3] < previous < current:
        phrase, bonus = "连续上涨", 0.7
    elif len(values) >= 3 and values[-3] > previous > current:
        phrase, bonus = "连续回落", 0.7
    elif abs(daily) <= 0.1:
        phrase, bonus = "窄幅震荡", 0.0
    else:
        phrase, bonus = ("小幅上涨", 0.0) if daily > 0 else ("小幅回落", 0.0)
    return Topic(market, phrase, abs(daily) + bonus, daily)


def _select_topic(data: dict) -> Topic:
    topics = [_topic_for(key, data.get(key, [])) for key in ("pakistan", "india")]
    available = [topic for topic in topics if topic is not None]
    if not available:
        raise ValueError("巴基斯坦和印度均无可用数据")
    return max(available, key=lambda topic: topic.score)


def build_daily_email(payload: dict) -> DailyEmail:
    data = payload["data"]
    topic = _select_topic(data)
    focus_rows = data[topic.market]
    latest_focus = focus_rows[-1]
    focus_name = "巴基斯坦" if topic.market == "pakistan" else "印度"
    topic_title = f"{focus_name}棉花{topic.phrase}"
    subject = f"{topic_title}｜昨日{_headline_price(focus_rows)}"

    lines = [subject, "", f"本期主题：{topic_title}",
             f"报价日期：{latest_focus['date']}", f"昨日价格：{_price(latest_focus)}",
             f"人民币参考：{latest_focus['cny_per_ton']:,.0f} 元/吨",
             f"较上一交易日：{_direction(topic.daily_change)} {abs(topic.daily_change):.2f}%", "", "四国最新报价"]
    focus_card = (
        f"<div style=\"background:#fff;padding:16px;border-radius:12px;margin-bottom:12px\">"
        f"<h2 style=\"margin-top:0\">{escape(topic_title)}</h2>"
        f"<p>报价日期：{escape(latest_focus['date'])}</p>"
        f"<p>昨日价格：<b>{escape(_price(latest_focus))}</b></p>"
        f"<p>人民币参考：<b>{latest_focus['cny_per_ton']:,.0f} 元/吨</b></p>"
        f"<p>较上一交易日：<b>{_direction(topic.daily_change)} {abs(topic.daily_change):.2f}%</b></p></div>"
    )
    rows = []
    for key in ("china", "usa", "pakistan", "india"):
        if not data.get(key):
            continue
        latest = data[key][-1]
        change = _change(data[key])
        lines.append(f"- {LABELS[key]}：{_price(latest)}；人民币 {latest['cny_per_ton']:,.0f} 元/吨；7日{_direction(change)}{abs(change):.2f}%")
        rows.append(
            "<tr>"
            f"<td>{escape(LABELS[key])}</td>"
            f"<td>{escape(_price(latest))}</td>"
            f"<td>{latest['cny_per_ton']:,.0f} 元/吨</td>"
            f"<td>{_direction(change)} {abs(change):.2f}%</td>"
            "</tr>"
        )
    lines += ["", "完整7日走势：", SITE_URL, "", "说明：休市日使用最近一个有报价的交易日，并在正文标注报价日期。",
              payload.get("disclaimer", "价格仅供市场参考，不构成交易建议。")]

    html = f"""<!doctype html><html><body style="margin:0;background:#f4efe5;color:#173f35;font-family:Arial,'Microsoft YaHei',sans-serif">
<div style="max-width:680px;margin:auto;padding:24px"><h1 style="font-size:25px">{escape(subject)}</h1>
<h2>今日主题</h2>{focus_card}
<h2>四国最新报价</h2><table style="width:100%;border-collapse:collapse;background:#fff"><tr><th>市场</th><th>原始价</th><th>人民币参考</th><th>7日走势</th></tr>{''.join(rows)}</table>
<p style="text-align:center;margin:28px"><a href="{SITE_URL}" style="background:#173f35;color:white;padding:12px 22px;text-decoration:none;border-radius:8px">打开四国棉价7日看板</a></p>
<p style="font-size:12px;color:#65756f">说明：休市日使用最近一个有报价的交易日，并在正文标注报价日期。</p>
<p style="font-size:12px;color:#65756f">{escape(payload.get('disclaimer', '价格仅供市场参考，不构成交易建议。'))}</p></div></body></html>"""
    return DailyEmail(subject=subject, plain="\n".join(lines), html=html)
