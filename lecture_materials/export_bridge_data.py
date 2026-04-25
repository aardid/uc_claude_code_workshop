"""Export cleaned bridge data with risk sub-scores to compact JSON for the interactive explorer."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bridge_risk_demo"))
from bridge_analysis import load_and_clean, compute_risk_score, INPUT_CSV, COLS

OUTPUT_DIR = Path(__file__).resolve().parent
JSON_PATH = OUTPUT_DIR / "bridge_data.json"


def main():
    df = load_and_clean(INPUT_CSV)
    df = compute_risk_score(df)

    records = []
    for _, row in df.iterrows():
        records.append([
            round(row["longitude"], 4),
            round(row["latitude"], 4),
            round(row["condition_risk"], 4),
            round(row["age_risk"], 4),
            round(row["traffic_risk"], 4),
        ])

    with open(JSON_PATH, "w") as f:
        json.dump(records, f, separators=(",", ":"))

    size_mb = JSON_PATH.stat().st_size / (1024 * 1024)
    print(f"Exported {len(records):,} bridges to {JSON_PATH}")
    print(f"File size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
