import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit
from mi_tracker.core import collect, digest, extract_items, event_rows

BILL = {
    "id": "mi-fixture-1", "identifier": "HB 9999",
    "title": "Synthetic test record, not a real bill",
    "source_url": "https://example.invalid/bill"
}

def fake_fetch(url):
    path = urlsplit(url).path
    if path.endswith("/bills"):
        return {"data": [BILL]}
    if path.endswith("/mi-fixture-1"):
        return {"data": BILL}
    category = path.rsplit("/", 1)[-1]
    responses = {
        "sponsors": [{"name": "Test Sponsor", "role": "primary"}],
        "actions": [{"description": "Introduced", "date": "2026-01-01"}],
        "versions": [{"title": "As introduced", "url": "https://example.invalid/text"}],
        "votes": [], "documents": []
    }
    if category in responses:
        return {"data": responses[category]}
    raise ValueError(url)

class TestCollector(unittest.TestCase):
    def test_extract_items(self):
        self.assertEqual(extract_items({"data": [1]}), [1])
        with self.assertRaises(ValueError):
            extract_items({"unexpected": []})

    def test_stable_hash(self):
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))

    def test_invalid_category_schema_is_error(self):
        with self.assertRaises(ValueError):
            list(event_rows("x", "sponsors", {"unexpected": []}))

    def test_idempotency(self):
        with tempfile.TemporaryDirectory() as path:
            db = Path(path) / "db.sqlite"
            out = Path(path) / "out"
            collect(db, out, fetch=fake_fetch, delay=0)
            collect(db, out, fetch=fake_fetch, delay=0)
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM bills").fetchone()[0], 1)
                self.assertEqual(con.execute("SELECT count(*) FROM evidence").fetchone()[0], 3)
            data = json.loads((out / "bills.json").read_text())
            self.assertEqual(data["run"]["success"], 1)
            self.assertEqual(len(data["bills"][0]["evidence"]), 3)

if __name__ == "__main__":
    unittest.main()
