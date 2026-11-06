"""Build a portable sales report from fictional CSV exports."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
import json
from pathlib import Path

REQUIRED = {"order_id", "date", "product", "category", "quantity", "unit_price"}
CENTS = Decimal("0.01")


def money(value: Decimal) -> str:
    return str(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def analyze(rows):
    revenue = Decimal("0")
    units = 0
    seen = set()
    by_month = defaultdict(lambda: Decimal("0"))
    by_category = defaultdict(lambda: Decimal("0"))
    by_product = defaultdict(lambda: Decimal("0"))
    orders = 0
    for index, row in enumerate(rows, start=2):
        try:
            identifier = (row.get("order_id") or "").strip()
            product = (row.get("product") or "").strip()
            category = (row.get("category") or "").strip()
            if not identifier or not product or not category:
                raise ValueError("missing order ID, product or category")
            if identifier in seen:
                raise ValueError("duplicate order ID")
            ordered = date.fromisoformat((row.get("date") or "").strip())
            quantity = int((row.get("quantity") or "").strip())
            price = Decimal((row.get("unit_price") or "").strip())
            if quantity <= 0 or price < 0 or not price.is_finite():
                raise ValueError("invalid quantity or price")
        except (ValueError, InvalidOperation) as exc:
            raise ValueError(f"CSV line {index}: {exc}") from exc
        seen.add(identifier)
        subtotal = price * quantity
        revenue += subtotal
        units += quantity
        orders += 1
        by_month[ordered.strftime("%Y-%m")] += subtotal
        by_category[category] += subtotal
        by_product[product] += subtotal
    return {
        "orders": orders,
        "units_sold": units,
        "revenue": money(revenue),
        "average_order_value": money(revenue / orders) if orders else "0.00",
        "monthly_revenue": {key: money(value) for key, value in sorted(by_month.items())},
        "category_revenue": {key: money(value) for key, value in sorted(by_category.items())},
        "product_revenue": {key: money(value) for key, value in sorted(by_product.items())},
    }


def render_html(report):
    categories = report["category_revenue"]
    max_value = max((Decimal(value) for value in categories.values()), default=Decimal("0"))
    bars = "".join(
        f'<div class="bar-row"><strong>{escape(name)}</strong>'
        f'<div class="track"><div class="fill" style="width:'
        f'{(Decimal(value) / max_value * 100) if max_value else 0:.1f}%"></div></div>'
        f'<span>$ {escape(value)}</span></div>'
        for name, value in categories.items()
    )
    rows = "".join(
        f'<tr><td>{escape(month)}</td><td>$ {escape(value)}</td></tr>'
        for month, value in report["monthly_revenue"].items()
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sales Intelligence — Demo Report</title>
<style>
body{{font:16px system-ui,sans-serif;background:#f3f6fb;color:#18243a;margin:0;padding:2rem}}
main{{max-width:850px;margin:auto}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem}}
.card,section{{background:white;border-radius:14px;padding:1.3rem;margin:1rem 0;box-shadow:0 3px 15px #19315a0a}}
.card b{{font-size:1.45rem;display:block}}.bar-row{{display:grid;grid-template-columns:130px 1fr 95px;gap:12px;align-items:center;margin:12px 0}}
.track{{background:#e4eaf6;border-radius:20px;overflow:hidden;height:20px}}.fill{{background:#476ef0;height:100%}}
table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #e5e7eb}}
small{{color:#5d6b80}}@media(max-width:500px){{.bar-row{{grid-template-columns:1fr}}}}
</style></head><body><main><h1>Sales Intelligence</h1>
<small>Illustrative sales data · generated offline · no personal information</small>
<div class="cards">
<div class="card">Revenue<b>$ {escape(report["revenue"])}</b></div>
<div class="card">Orders<b>{report["orders"]}</b></div>
<div class="card">Units sold<b>{report["units_sold"]}</b></div>
<div class="card">Average order<b>$ {escape(report["average_order_value"])}</b></div>
</div><section><h2>Revenue by category</h2>{bars or "<p>No records.</p>"}</section>
<section><h2>Monthly revenue</h2><table><thead><tr><th>Month</th><th>Revenue</th></tr></thead>
<tbody>{rows}</tbody></table></section></main></body></html>"""


def process(source: Path, report_path: Path, html_path: Path):
    paths = [source.resolve(), report_path.resolve(), html_path.resolve()]
    if len(set(paths)) != 3:
        raise ValueError("input and output paths must be different")
    with source.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError(f"Required columns: {', '.join(sorted(REQUIRED))}")
        result = analyze(reader)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    html_path.write_text(render_html(result), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description="Offline sales dashboard generator")
    parser.add_argument("source", type=Path)
    parser.add_argument("--json", type=Path, default=Path("report.json"))
    parser.add_argument("--html", type=Path, default=Path("dashboard.html"))
    args = parser.parse_args()
    report = process(args.source, args.json, args.html)
    print(f"Orders: {report['orders']} | Revenue: $ {report['revenue']}")


if __name__ == "__main__":
    main()
