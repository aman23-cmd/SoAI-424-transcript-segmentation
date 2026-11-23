"""Initial annotator agreement and a DRAFT merge of boundaries.

Reads data/annotations.csv (annotator column: A1, A2). For each video:
  - Boundary F1 (+/-30 s) and Pk between A1 (reference) and A2
  - boundaries marked by both within +/-30 s are merged (final time = mean)
  - boundaries marked by only one annotator go to data/boundaries_to_discuss.csv
After discussing, write the agreed boundaries to data/boundaries_final.csv by hand, then freeze it.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.metrics import WordTimeline, boundary_prf, pk_windowdiff, window_k
from src.transcript import load_transcript

TOL = 30.0


def pairs(R, P, tol=TOL):
    R, P = sorted(R), sorted(P)
    i = j = 0
    matched, only_r, only_p = [], [], []
    while i < len(R) and j < len(P):
        if P[j] < R[i] - tol:
            only_p.append(P[j]); j += 1
        elif P[j] > R[i] + tol:
            only_r.append(R[i]); i += 1
        else:
            matched.append((R[i], P[j])); i += 1; j += 1
    only_r += R[i:]; only_p += P[j:]
    return matched, only_r, only_p


ann = defaultdict(lambda: defaultdict(list))
with open("data/annotations.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["video_id"].strip():
            ann[r["video_id"]][r["annotator"].strip()].append(float(r["boundary_time_sec"]))

merged, discuss = [], []
print("video_id, boundary_F1(A1 vs A2), Pk, merged, to_discuss")
for vid, d in ann.items():
    a1, a2 = d.get("A1", []), d.get("A2", [])
    _, _, f1 = boundary_prf(a1, a2, TOL)
    tl = WordTimeline(load_transcript(vid))
    r_w = [tl.position(t) for t in a1]; h_w = [tl.position(t) for t in a2]
    pk, _ = pk_windowdiff(r_w, h_w, tl.total_words, window_k(r_w, tl.total_words))
    m, only1, only2 = pairs(a1, a2)
    for x, y in m:
        merged.append({"video_id": vid, "boundary_time_sec": round((x + y) / 2, 1)})
    for t in only1:
        discuss.append({"video_id": vid, "boundary_time_sec": t, "annotator": "A1"})
    for t in only2:
        discuss.append({"video_id": vid, "boundary_time_sec": t, "annotator": "A2"})
    print(f"{vid}, {f1:.3f}, {pk:.3f}, {len(m)}, {len(only1) + len(only2)}")

for name, rows, keys in (("data/boundaries_merged_draft.csv", merged, ["video_id", "boundary_time_sec"]),
                         ("data/boundaries_to_discuss.csv", discuss, ["video_id", "boundary_time_sec", "annotator"])):
    with open(name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
print("Wrote data/boundaries_merged_draft.csv and data/boundaries_to_discuss.csv")
