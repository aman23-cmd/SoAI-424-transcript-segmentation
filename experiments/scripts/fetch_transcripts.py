"""Download and store transcripts for every video in data/videos.csv (needs internet).
Transcripts are stored locally in data/transcripts/ and are git-ignored (not redistributed)."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.transcript import fetch_and_save

with open("data/videos.csv", newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    print("Columns:", reader.fieldnames)

    rows = list(reader)

    print("Total rows:", len(rows))

    for row in rows:
        print("ROW:", row)

    ids = [r["video_id"].strip() for r in rows if r["video_id"].strip()]
    print("IDs:", ids)

for vid in ids:
    if (Path("data/transcripts") / f"{vid}.json").exists():
        print(f"{vid}: already downloaded"); continue
    try:
        path, n = fetch_and_save(vid)
        print(f"{vid}: {n} caption lines -> {path}")
    except Exception as e:
        print(f"{vid}: FAILED ({type(e).__name__}: {e}). Exclude this video or retry later.")

print("Script started")

with open("data/videos.csv", newline="", encoding="utf-8") as f:
    ids = [r["video_id"].strip() for r in csv.DictReader(f) if r["video_id"].strip()]

print("IDs:", ids)
print("Count:", len(ids))
