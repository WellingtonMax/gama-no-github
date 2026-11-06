import csv
from decimal import Decimal
from html import escape
import io
from pathlib import Path
import tempfile
import unittest

from report import analyze, render_html, process

SAMPLE = """order_id,date,product,category,quantity,unit_price
1001,2026-11-01,Notebook,Office,2,12.50
1002,2026-11-02,Pencil,Office,10,1.00
1003,2026-10-21,Flask,Home,1,25.00
"""


class ReportTests(unittest.TestCase):
    def rows(self, text=SAMPLE):
        return list(csv.DictReader(io.StringIO(text)))

    def test_correct_kpis(self):
        result = analyze(self.rows())
        self.assertEqual(result["orders"], 3)
        self.assertEqual(result["units_sold"], 13)
        self.assertEqual(result["revenue"], "60.00")
        self.assertEqual(result["average_order_value"], "20.00")
        self.assertEqual(result["category_revenue"]["Office"], "35.00")

    def test_reject_duplicate(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyze(self.rows() + self.rows()[:1])

    def test_reject_negative_price(self):
        rows = self.rows()
        rows[0]["unit_price"] = "-10"
        with self.assertRaisesRegex(ValueError, "invalid"):
            analyze(rows)

    def test_html_escapes_untrusted_labels(self):
        result = analyze(self.rows())
        result["category_revenue"] = {"<script>alert(1)</script>": "50.00"}
        page = render_html(result)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)

    def test_pipeline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "source.csv").write_text(SAMPLE, encoding="utf-8")
            result = process(root / "source.csv", root / "out.json", root / "out.html")
            self.assertEqual(result["revenue"], "60.00")
            self.assertTrue((root / "out.html").read_text().startswith("<!doctype html>"))


if __name__ == "__main__":
    unittest.main()
