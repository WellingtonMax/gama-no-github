import csv
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from bridge import export_rows, fetch_json, safe_csv, validate_url


class FakeResponse:
    def __init__(self, payload):
        self.buffer = BytesIO(payload)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.buffer.close()
    def read(self, size):
        return self.buffer.read(size)


class BridgeTests(unittest.TestCase):
    def test_only_authorized_https(self):
        for url in ("http://api.example.org/items", "https://not-allowed.example/items",
                    "https://api.example.org:8080/items"):
            with self.assertRaises(ValueError):
                validate_url(url, {"api.example.org"})

    def test_fetch_list_without_network(self):
        captured = {}
        def fake_transport(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeResponse(b'[{"id":1,"name":"A"}]')
        rows = fetch_json("https://api.example.org/items", {"api.example.org"},
                          transport=fake_transport)
        self.assertEqual(rows, [{"id": 1, "name": "A"}])
        self.assertEqual(captured["timeout"], 10)

    def test_fetch_data_envelope(self):
        def fake_transport(request, timeout):
            return FakeResponse(b'{"data":[{"id":2}]}')
        rows = fetch_json("https://api.example.org/items", {"api.example.org"},
                          transport=fake_transport)
        self.assertEqual(rows[0]["id"], 2)

    def test_reject_malformed_shape(self):
        with self.assertRaises(ValueError):
            fetch_json("https://api.example.org/items", {"api.example.org"},
                       transport=lambda request, timeout: FakeResponse(b'{"items":"bad"}'))

    def test_csv_formula_protection(self):
        self.assertEqual(safe_csv("=SUM(1)"), "'=SUM(1)")
        self.assertEqual(safe_csv("@admin"), "'@admin")

    def test_export(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "out.csv"
            self.assertEqual(export_rows([{"id": 1, "name": "Alice"}], ["id", "name"], output), 1)
            with output.open(encoding="utf-8", newline="") as stream:
                self.assertEqual(list(csv.DictReader(stream))[0], {"id": "1", "name": "Alice"})


if __name__ == "__main__":
    unittest.main()
