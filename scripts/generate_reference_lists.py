#!/usr/bin/env python3

import csv
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    ROOT
    / "frontend"
    / "public"
    / "data"
    / "references"
)

CWE_URL = "https://cwe.mitre.org/data/csv/2000.csv.zip"

CAPEC_URL = (
    "https://capec.mitre.org/data/csv/2000.csv.zip"
)


def generate_cwe():
    print("Fetching CWE data...")

    with urlopen(CWE_URL, timeout=120) as response:
        archive_data = response.read()

    with ZipFile(io.BytesIO(archive_data)) as archive:
        csv_files = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv")
        ]

        if not csv_files:
            raise RuntimeError(
                "CWE archive contains no CSV file"
            )

        with archive.open(csv_files[0]) as csv_file:
            reader = csv.DictReader(
                io.TextIOWrapper(
                    csv_file,
                    encoding="utf-8-sig",
                )
            )

            items = [
                {
                    "id": f"CWE-{row['CWE-ID']}",
                    "name": row["Name"],
                }
                for row in reader
                if row.get("CWE-ID") and row.get("Name")
            ]

    items.sort(
        key=lambda item: int(item["id"].split("-")[1])
    )

    write_reference_list("cwe", items)


def generate_capec():
    print("Fetching CAPEC data...")

    with urlopen(CAPEC_URL, timeout=120) as response:
        archive_data = response.read()

    with ZipFile(io.BytesIO(archive_data)) as archive:
        csv_files = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv")
        ]

        if not csv_files:
            raise RuntimeError(
                "CAPEC archive contains no CSV file"
            )

        with archive.open(csv_files[0]) as csv_file:
            reader = csv.DictReader(
                io.TextIOWrapper(
                    csv_file,
                    encoding="utf-8-sig",
                )
            )

            # Normalize column names such as "'ID" -> "ID"
            if reader.fieldnames:
                reader.fieldnames = [
                    field.strip().strip("'\"")
                    for field in reader.fieldnames
                ]

            items = []

            for row in reader:
                capec_id = row.get("ID")
                name = row.get("Name")

                if not capec_id or not name:
                    continue

                capec_id = capec_id.strip().strip("'\"")
                name = name.strip()

                if not capec_id or not name:
                    continue

                items.append(
                    {
                        "id": f"CAPEC-{capec_id}",
                        "name": name,
                    }
                )

    if not items:
        raise RuntimeError(
            "No CAPEC entries were parsed from the CSV"
        )

    items.sort(
        key=lambda item: int(
            item["id"].split("-")[1]
        )
    )

    write_reference_list(
        "capec",
        items,
    )


def write_reference_list(name, items):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = OUTPUT_DIR / f"{name}.json"

    with output.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {"items": items},
            file,
            indent=2,
            ensure_ascii=False,
        )

        file.write("\n")

    print(
        f"Wrote {len(items)} entries to {output}"
    )


def main():
    generate_cwe()
    generate_capec()


if __name__ == "__main__":
    main()
