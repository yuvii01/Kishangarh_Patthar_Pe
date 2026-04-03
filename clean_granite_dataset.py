#!/usr/bin/env python3
"""Clean Granite Dealers dataset.

Keeps only these columns: store_name, contact_number, address, city.
Drops rows where contact_number is empty/missing or contains "send to phone" (case-insensitive).
"""

import csv
import os
import re

INPUT_CSV = "granite_dealers_rajasthan.csv"
OUTPUT_CSV = "granite_dealers_rajasthan_clean.csv"


def is_valid_contact(contact: str) -> bool:
    if not contact:
        return False
    contact = contact.strip()
    if not contact:
        return False
    if re.search(r"(?i)send\s*to\s*phone", contact):
        return False
    return True


def main():
    cwd = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(cwd, INPUT_CSV)
    output_path = os.path.join(cwd, OUTPUT_CSV)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    kept = 0
    dropped = 0

    with open(input_path, newline="", encoding="utf-8-sig") as fin:
        reader = csv.DictReader(fin)
        fieldnames_out = ["store_name", "contact_number", "address", "city"]

        with open(output_path, "w", newline="", encoding="utf-8-sig") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames_out)
            writer.writeheader()

            for row in reader:
                store_name = (row.get("store_name") or "").strip()
                contact_number = (row.get("contact_number") or "").strip()
                address = (row.get("address") or "").strip()
                city = (row.get("city") or "").strip()

                if not store_name or not address or not city:
                    dropped += 1
                    continue

                if not is_valid_contact(contact_number):
                    dropped += 1
                    continue

                writer.writerow({
                    "store_name": store_name,
                    "contact_number": contact_number,
                    "address": address,
                    "city": city,
                })
                kept += 1

    print(f"Cleaned dataset written to: {output_path}")
    print(f"Kept rows: {kept}")
    print(f"Dropped rows: {dropped}")


if __name__ == "__main__":
    main()
