# Sales Intelligence — Offline KPI Dashboard

**Client problem:** sales CSV exports contain numbers but not usable insights.

**Deliverables:** JSON KPIs, stand-alone HTML report, readable Python source and repeatable unit tests.

## Run

```bash
cd portfolio/02-sales-intelligence
python report.py sample_sales.csv --json report.json --html dashboard.html
python -m unittest test_report.py -v
```

Open `dashboard.html` locally; no hosting or external services required.

**Metrics:** revenue, distinct orders, units sold, average order value, monthly revenue, category revenue and product revenue. Decimal arithmetic avoids binary floating-point currency errors; HTML output escapes user-provided product/category labels.

**Assumptions:** CSV values represent completed positive-quantity sales; each row uses a unique order ID. No returns, taxes, FX, shipping or discounts are inferred. No real customer records are included.

**Demonstration only:** fictional data, not client results.
