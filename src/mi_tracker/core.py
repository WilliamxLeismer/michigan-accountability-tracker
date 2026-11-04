"""Evidence-first ingestion of free public legislative data.

The collector indexes evidence; it does not infer political intentions.
"""
import hashlib
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.billcommons.org/api/v1"
SCHEMA = """
CREATE TABLE IF NOT EXISTS bills (
    id TEXT PRIMARY KEY, identifier TEXT, title TEXT, session TEXT,
    jurisdiction TEXT, source_url TEXT, fetched_at TEXT,
    raw_sha256 TEXT, raw_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY, bill_id TEXT NOT NULL, category TEXT NOT NULL,
    label TEXT, actor TEXT, occurred_at TEXT, source_url TEXT,
    raw_json TEXT NOT NULL, FOREIGN KEY(bill_id) REFERENCES bills(id)
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, completed_at TEXT,
    success INTEGER, bills_seen INTEGER, records_seen INTEGER, error TEXT
);
"""

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def request_json(url, retries=3):
    """Respect endpoint throttling; never evade blocks or access controls."""
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "MichiganAccountabilityTracker/0.1 (public, nonpartisan research)",
        })
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            time.sleep(min(60, int(retry_after) if retry_after.isdecimal() else 2 ** attempt))
        except (TimeoutError, urllib.error.URLError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)

def extract_items(response):
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        for key in ("data", "results", "items"):
            if isinstance(response.get(key), list):
                return response[key]
    raise ValueError("Unexpected collection schema")

def pick(obj, *names):
    return next((obj[n] for n in names if obj.get(n) not in (None, "")), None)

def source_of(obj):
    result = pick(obj, "source_url", "url", "source")
    if isinstance(result, dict):
        return pick(result, "url", "href")
    return result if isinstance(result, str) else None

def event_rows(bill_id, category, response):
    if isinstance(response, dict) and isinstance(response.get("data"), (dict, list)):
        response = response["data"]
    if isinstance(response, dict):
        found = next((response[k] for k in (category, "items", "results")
                      if isinstance(response.get(k), list)), None)
        if found is None:
            raise ValueError("Unexpected " + category + " schema")
        response = found
    if not isinstance(response, list):
        raise ValueError("Unexpected " + category + " schema")
    for entry in response:
        if not isinstance(entry, dict):
            raise ValueError("Non-object evidence record")
        event_id = digest([bill_id, category, entry])
        yield (
            event_id, bill_id, category,
            str(pick(entry, "description", "title", "name", "type", "action") or category),
            str(pick(entry, "person_name", "name", "sponsor", "actor") or ""),
            str(pick(entry, "date", "action_date", "occurred_at") or ""),
            source_of(entry), canonical(entry)
        )

def export(con, out_dir):
    con.row_factory = sqlite3.Row
    bills = []
    for row in con.execute("SELECT * FROM bills ORDER BY identifier LIMIT 500"):
        bill = dict(row)
        bill.pop("raw_json", None)
        bill["evidence"] = [
            {k: v for k, v in dict(event).items() if k != "raw_json"}
            for event in con.execute(
                "SELECT * FROM evidence WHERE bill_id=? ORDER BY category, occurred_at",
                (bill["id"],)
            )
        ]
        bills.append(bill)
    run = con.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    (out_dir / "bills.json").write_text(
        json.dumps({"bills": bills, "run": dict(run) if run else None},
                   indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

def collect(db_path, out_dir, per_page=10, max_pages=1, fetch=request_json, delay=0.4):
    if not 1 <= per_page <= 100 or not 1 <= max_pages <= 100:
        raise ValueError("Invalid collection bounds")
    db_path = Path(db_path)
    out_dir = Path(out_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    run_id = con.execute(
        "INSERT INTO runs(started_at,success,bills_seen,records_seen) VALUES (?,0,0,0)",
        (now(),)
    ).lastrowid
    con.commit()
    bills_seen = records_seen = 0
    warnings = []
    try:
        for page in range(1, max_pages + 1):
            query = urllib.parse.urlencode({
                "jurisdiction": "MI", "page": page, "per_page": per_page
            })
            items = extract_items(fetch(BASE + "/bills?" + query))
            if not items:
                break
            for summary in items:
                bill_id = str(pick(summary, "id", "bill_id") or "")
                if not bill_id:
                    raise ValueError("Bill without stable ID")
                path = BASE + "/bills/" + urllib.parse.quote(bill_id, safe="")
                detail = fetch(path)
                if isinstance(detail, dict) and isinstance(detail.get("data"), dict):
                    detail = detail["data"]
                if not isinstance(detail, dict):
                    raise ValueError("Unexpected bill detail schema")
                identifier = pick(detail, "identifier", "bill_number") or pick(
                    summary, "identifier", "bill_number"
                )
                if not identifier:
                    raise ValueError("Missing bill identifier")
                con.execute(
                    "INSERT OR REPLACE INTO bills VALUES (?,?,?,?,?,?,?,?,?)",
                    (bill_id, str(identifier), str(pick(detail, "title", "name") or ""),
                     str(pick(detail, "session", "session_id") or ""), "MI",
                     source_of(detail) or source_of(summary), now(),
                     digest(detail), canonical(detail))
                )
                bills_seen += 1
                for category in ("sponsors", "actions", "versions", "votes", "documents"):
                    try:
                        events = fetch(path + "/" + category)
                        for row in event_rows(bill_id, category, events):
                            con.execute(
                                "INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?)", row
                            )
                            records_seen += 1
                    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
                        warnings.append(f"{identifier} {category}: {exc}")
                    if delay:
                        time.sleep(delay)
                con.commit()
                if delay:
                    time.sleep(delay)
            if len(items) < per_page:
                break
        con.execute(
            "UPDATE runs SET completed_at=?, success=?, bills_seen=?, records_seen=?, error=? WHERE id=?",
            (now(), int(not warnings), bills_seen, records_seen,
             "\n".join(warnings), run_id)
        )
        con.commit()
    except Exception as exc:
        con.execute("UPDATE runs SET completed_at=?, error=? WHERE id=?",
                    (now(), str(exc), run_id))
        con.commit()
        raise
    finally:
        export(con, out_dir)
        con.close()
    return {"bills_seen": bills_seen, "records_seen": records_seen, "warnings": warnings}
