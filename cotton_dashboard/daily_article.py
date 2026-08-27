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


def build_daily_email(payload: dict) -> DailyEmail:
    data = payload["data"]
    available = [key for key in ("pakistan", "india") if data.get(key)]
    if not available:
        raise ValueError("巴基斯坦和印度均无可用数据")
    focus = max(available, key=lambda key: abs(_change(data[key])))
    focus_change = _change(data[focus])
    focus_name = "巴基斯坦" if focus == "pakistan" else "印度"
    subject = f"{focus_name}棉价7日{_direction(focus_change)}{abs(focus_change):.2f}%｜四国棉价日报"

    lines = [subject, "", f"重点市场：{focus_name}棉花", f"最新报价：{_price(data[focus][-1])}",
             f"人民币参考：{data[focus][-1]['cny_per_ton']:,.0f} 元/吨", "", "四国最新报价"]
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
    lines += ["", "完整7日走势：", SITE_URL, "", payload.get("disclaimer", "价格仅供市场参考，不构成交易建议。")]

    html = f"""<!doctype html><html><body style="margin:0;background:#f4efe5;color:#173f35;font-family:Arial,'Microsoft YaHei',sans-serif">
<div style="max-width:680px;margin:auto;padding:24px"><h1 style="font-size:25px">{escape(subject)}</h1>
<div style="background:#fff;padding:18px;border-radius:12px"><h2>{focus_name}棉花走势</h2>
<p>最新报价：<b>{escape(_price(data[focus][-1]))}</b></p>
<p>人民币参考：<b>{data[focus][-1]['cny_per_ton']:,.0f} 元/吨</b></p></div>
<h2>四国最新报价</h2><table style="width:100%;border-collapse:collapse;background:#fff"><tr><th>市场</th><th>原始价</th><th>人民币参考</th><th>7日走势</th></tr>{''.join(rows)}</table>
<p style="text-align:center;margin:28px"><a href="{SITE_URL}" style="background:#173f35;color:white;padding:12px 22px;text-decoration:none;border-radius:8px">打开四国棉价7日看板</a></p>
<p style="font-size:12px;color:#65756f">{escape(payload.get('disclaimer', '价格仅供市场参考，不构成交易建议。'))}</p></div></body></html>"""
    return DailyEmail(subject=subject, plain="\n".join(lines), html=html)
