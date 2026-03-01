from __future__ import annotations

import csv
import sys
from pathlib import Path

# Input: Census Gazetteer ZCTA national file (tab-delimited)
# Output: adoption/data/us_zip_centroids.csv with headers zip,lat,lon

def main(in_path: str, out_path: str) -> int:
    in_file = Path(in_path)
    out_file = Path(out_path)
    if not in_file.exists():
        print(f"Input not found: {in_file}", file=sys.stderr)
        return 2

    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Gazetteer columns include GEOID, INTPTLAT, INTPTLONG
    # GEOID is the 5-digit ZCTA code; lat/lon are representative internal point coords.
    with in_file.open("r", encoding="utf-8", newline="") as fin, out_file.open("w", encoding="utf-8", newline="") as fout:
        reader = csv.DictReader(fin, delimiter="\t")
        writer = csv.DictWriter(fout, fieldnames=["zip", "lat", "lon"])
        writer.writeheader()

        written = 0
        for row in reader:
            geoid = (row.get("GEOID") or "").strip()
            lat = (row.get("INTPTLAT") or "").strip()
            lon = (row.get("INTPTLONG") or "").strip()

            if len(geoid) != 5:
                continue
            try:
                float(lat); float(lon)
            except ValueError:
                continue

            writer.writerow({"zip": geoid, "lat": lat, "lon": lon})
            written += 1

    print(f"Wrote {written} rows -> {out_file}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/build_zip_centroids.py <input_gazetteer_txt> <output_csv>", file=sys.stderr)
        sys.exit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))