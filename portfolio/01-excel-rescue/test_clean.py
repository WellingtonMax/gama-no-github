import csv
from pathlib import Path
import tempfile
import unittest

from clean import clean_rows, normalize, process, safe_cell


class CleanerTests(unittest.TestCase):
    def test_normalize(self):
        record = normalize({"name": " Alice   Smith ", "email": " ALICE@Example.COM ",
                            "signup_date": "05/11/2026", "city": " Brasilia "})
        self.assertEqual(record["email"], "alice@example.com")
        self.assertEqual(record["signup_date"], "2026-11-05")
        self.assertEqual(record["name"], "Alice Smith")

    def test_rejects_duplicate_and_invalid(self):
        rows = [
            {"name": "A", "email": "a@test.com", "signup_date": "", "city": ""},
            {"name": "A", "email": "A@TEST.COM", "signup_date": "", "city": ""},
            {"name": "B", "email": "invalid", "signup_date": "", "city": ""},
        ]
        good, bad = clean_rows(rows)
        self.assertEqual(len(good), 1)
        self.assertEqual([x["reason"] for x in bad], ["duplicate email", "invalid email"])

    def test_formula_injection(self):
        self.assertEqual(safe_cell(" =HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(safe_cell("-SUM(1)"), "'-SUM(1)")

    def test_missing_name(self):
        with self.assertRaisesRegex(ValueError, "missing name"):
            normalize({"name": "", "email": "a@test.com"})

    def test_file_pipeline(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "input.csv"
            source.write_text("name,email,signup_date,city\nA,a@test.com,2026-11-05,City\n",
                              encoding="utf-8")
            accepted, rejected = process(source, base / "out.csv", base / "bad.csv")
            self.assertEqual((accepted, rejected), (1, 0))
            with (base / "out.csv").open(newline="", encoding="utf-8") as stream:
                self.assertEqual(list(csv.DictReader(stream))[0]["email"], "a@test.com")


if __name__ == "__main__":
    unittest.main()
