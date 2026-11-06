"""Clean CRM CSV exports using Python's standard library only."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, date
from pathlib import Path
import re

FIELDS = ("name", "email", "signup_date", "city")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def safe_cell(value: str) -> str:
    """Prevent spreadsheet formula interpretation in free-text fields."""
    value = " ".join(str(value or "").split())
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def normalize_date(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("invalid date")


def normalize(row: dict[str, str]) -> dict[str, str]:
    email = str(row.get("email") or "").strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("invalid email")
    name = safe_cell(row.get("name") or "")
    if not name:
        raise ValueError("missing name")
    return {
        "name": name,
        "email": email,
        "signup_date": normalize_date(row.get("signup_date") or ""),
        "city": safe_cell(row.get("city") or ""),
    }


def clean_rows(rows):
    cleaned, rejected, seen = [], [], set()
    for number, row in enumerate(rows, start=2):
        try:
            record = normalize(row)
            if record["email"] in seen:
                raise ValueError("duplicate email")
            seen.add(record["email"])
            cleaned.append(record)
        except ValueError as exc:
            rejected.append({"line": number, "reason": str(exc)})
    return cleaned, rejected


def process(source: Path, destination: Path, rejects_file: Path) -> tuple[int, int]:
    if source.resolve() in {destination.resolve(), rejects_file.resolve()}:
        raise ValueError("input and output paths must differ")
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or any(key not in reader.fieldnames for key in FIELDS):
            raise ValueError("required columns: " + ", ".join(FIELDS))
        cleaned, rejected = clean_rows(reader)
    for path in (destination, rejects_file):
        path.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(cleaned)
    with rejects_file.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("line", "reason"))
        writer.writeheader()
        writer.writerows(rejected)
    return len(cleaned), len(rejected)


def main():
    parser = argparse.ArgumentParser(description="Clean a CRM CSV safely")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("cleaned.csv"))
    parser.add_argument("--rejects", type=Path, default=Path("rejected.csv"))
    args = parser.parse_args()
    good, bad = process(args.source, args.output, args.rejects)
    print(f"Accepted: {good}; rejected: {bad}")


if __name__ == "__main__":
    main()
