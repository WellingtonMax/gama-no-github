"""Export approved HTTPS JSON API records to CSV, without external packages."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

MAX_BYTES = 2_000_000
RETRY_CODES = {429, 500, 502, 503, 504}


class RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirects require explicit review and are disabled")


def validate_url(url: str, allowed_hosts: set[str]):
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.port not in (None, 443)):
        raise ValueError("Only HTTPS URLs without credentials or nonstandard ports are accepted")
    if parts.hostname.lower() not in {host.lower() for host in allowed_hosts}:
        raise ValueError("API hostname is not on the allowlist")
    return url


def fetch_json(url: str, allowed_hosts: set[str], transport=None,
               attempts: int = 3, sleeper=time.sleep):
    """Fetch a small JSON collection; transport injection makes tests network-free."""
    validate_url(url, allowed_hosts)
    if not 1 <= attempts <= 5:
        raise ValueError("attempts must be between 1 and 5")
    if transport is None:
        transport = build_opener(RefuseRedirects()).open
    headers = {"Accept": "application/json", "User-Agent": "Portfolio-API-Bridge/1.0"}
    token = os.getenv("API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers, method="GET")
    for attempt in range(attempts):
        try:
            with transport(request, timeout=10) as response:
                payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise ValueError("API response exceeds 2 MB limit")
                data = json.loads(payload.decode("utf-8"))
            records = data.get("data") if isinstance(data, dict) else data
            if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
                raise ValueError("JSON must be a list of objects or {'data': [objects]}")
            return records
        except HTTPError as exc:
            if exc.code not in RETRY_CODES or attempt == attempts - 1:
                raise RuntimeError(f"API returned HTTP {exc.code}") from exc
        except URLError as exc:
            if attempt == attempts - 1:
                raise RuntimeError("API connection failed") from exc
        sleeper(min(2 ** attempt, 4))
    raise RuntimeError("API request exhausted retries")


def safe_csv(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def export_rows(records: list[dict], fields: list[str], destination: Path):
    if not fields or len(fields) != len(set(fields)):
        raise ValueError("Provide distinct field names")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({field: safe_csv(record.get(field)) for field in fields})
    return len(records)


def main():
    parser = argparse.ArgumentParser(description="Approved HTTPS API -> CSV export")
    parser.add_argument("--url", required=True, help="Authorized HTTPS JSON API endpoint")
    parser.add_argument("--host", required=True, action="append", help="Explicitly allowed hostname")
    parser.add_argument("--field", required=True, action="append", help="Field to export, repeatable")
    parser.add_argument("--output", type=Path, default=Path("api-export.csv"))
    args = parser.parse_args()
    records = fetch_json(args.url, set(args.host))
    print(f"Exported {export_rows(records, args.field, args.output)} records")


if __name__ == "__main__":
    main()
