import csv, json
from pathlib import Path

rows = [r for r in csv.DictReader(open("data/videos.csv", encoding="utf-8")) if r["video_id"].strip()]
Path("data/transcripts_txt").mkdir(exist_ok=True)
for r in rows:
    vid = r["video_id"].strip()
    lines = json.load(open(f"data/transcripts/{vid}.json", encoding="utf-8"))
    with open(f"data/transcripts_txt/{vid}.txt", "w", encoding="utf-8") as f:
        for l in lines:
            m, s = divmod(int(l["start"]), 60)
            f.write(f"[{m:02d}:{s:02d}] {l['text'].replace(chr(10), ' ')}\n")
    print(vid, "saved")