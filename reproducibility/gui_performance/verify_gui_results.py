#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
import sys


EXPECTED = [
    "EEG preprocessing",
    "EEG feature extraction",
    "fNIRS preprocessing",
    "fNIRS feature extraction",
    "ET preprocessing",
    "ET feature extraction",
]


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser(description="Verify M3 GUI performance results")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--session", required=True)
    args = parser.parse_args()

    raw_path = args.results / "gui_raw_results.csv"
    summary_path = args.results / "gui_summary_results.csv"
    environment_path = args.results / "gui_environment.json"
    missing = [path for path in (raw_path, summary_path, environment_path) if not path.exists()]
    if missing:
        for path in missing:
            print("[MISSING] {}".format(path))
        return 1

    rows = [row for row in read_csv(raw_path) if row["session"] == args.session]
    summaries = [row for row in read_csv(summary_path) if row["session"] == args.session]
    summary_by_operation = {row["operation"]: row for row in summaries}
    failed = False

    print("Session: {}".format(args.session))
    print("Raw records: {}".format(len(rows)))
    print("")
    for operation in EXPECTED:
        group = [row for row in rows if row["operation"] == operation]
        warmups = [row for row in group if row["phase"] == "warmup"]
        measured = [
            row for row in group
            if row["phase"] == "measured" and row["included_in_summary"].lower() == "true"
        ]
        raised = [row for row in group if row["status"] == "raised"]
        summary_n = int(summary_by_operation.get(operation, {}).get("n", 0))
        ok = len(warmups) == 1 and len(measured) == 20 and summary_n == 20 and not raised
        print(
            "[{}] {}: warm-up={}, measured={}, summary n={}, raised={}".format(
                "OK" if ok else "CHECK",
                operation,
                len(warmups),
                len(measured),
                summary_n,
                len(raised),
            )
        )
        failed = failed or not ok

    print("")
    if failed:
        print("Verification incomplete. Finish or repeat the items marked CHECK.")
        return 1
    print("All six operations contain one warm-up and 20 summarized GUI-click measurements.")
    print("Also confirm the success notification and saved output for every click.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
