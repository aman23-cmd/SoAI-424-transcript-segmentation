import csv
from collections import Counter

vids = [r for r in csv.DictReader(open("data/videos.csv", encoding="utf-8")) if r["video_id"].strip()]
a = Counter(r["video_id"].strip() for r in csv.DictReader(open("data/annotations.csv", encoding="utf-8")))
b = Counter(r["video_id"].strip() for r in csv.DictReader(open("data/boundaries_final.csv", encoding="utf-8")))
q = Counter(r["video_id"].strip() for r in csv.DictReader(open("data/queries.csv", encoding="utf-8")))
print("video_id | split | annotations | final_boundaries | queries")
for v in vids:
    i = v["video_id"].strip()
    print(f"{i} | {v['split']} | {a[i]} | {b[i]} | {q[i]}")