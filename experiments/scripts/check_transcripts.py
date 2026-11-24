import csv, json
from pathlib import Path

rows = list(csv.DictReader(open("data/videos.csv", encoding="utf-8")))
print("video_id | split | minutes | caption_lines | words")
for r in rows:
    vid = r["video_id"].strip()
    if not vid:
        continue
    p = Path("data/transcripts") / f"{vid}.json"
    if not p.exists():
        print(vid, "| NO TRANSCRIPT")
        continue
    lines = json.loads(p.read_text(encoding="utf-8"))
    mins = (lines[-1]["start"] + lines[-1]["duration"]) / 60
    words = sum(len(l["text"].split()) for l in lines)
    print(f"{vid} | {r['split']} | {mins:.1f} | {len(lines)} | {words}")