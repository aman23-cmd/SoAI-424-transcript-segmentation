"""Builds a small synthetic dataset and runs the whole pipeline with the hashing embedder.
Checks that the code runs end to end and that the metric functions behave. NOT a result."""
import csv
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.metrics import (WordTimeline, boundary_prf, mrr, pk_windowdiff, random_reference,
                         recall_at_k, window_k)

# ---- unit checks on the metric functions
assert boundary_prf([100, 200], [105, 195], 30) == (1.0, 1.0, 1.0)
assert boundary_prf([100, 200], [100], 30)[2] == 2 * 1.0 * 0.5 / 1.5
assert boundary_prf([], [10], 30) == (0.0, 0.0, 0.0)
assert boundary_prf([100], [60, 90, 130], 30)[0] == 1 / 3          # one-to-one: only one match allowed
assert mrr([1, 2, 4]) == (1 + 0.5 + 0.25) / 3 and recall_at_k([1, 2, 4], 3) == 2 / 3
r = random_reference(4, [1, 3]); assert abs(r["random_mrr"] - (1 + .5 + 1/3 + .25) / 4) < 1e-9
lines = [{"text": "a b c d", "start": 0.0, "duration": 5.0}, {"text": "e f g h", "start": 5.0, "duration": 5.0}]
tl = WordTimeline(lines); assert tl.total_words == 8 and tl.position(5.0) == 4 and tl.position(7.5) == 6
assert pk_windowdiff([4], [4], 8, 2) == (0.0, 0.0)
print("metric unit checks passed")

# ---- synthetic dataset: 3 topics with disjoint vocabularies, 4 videos (2 dev, 2 test)
random.seed(1)
pools = {t: [f"{t}{i}" for i in range(25)] for t in ("alpha", "beta", "gamma")}
common = ["the", "and", "we", "now", "so"]
data = ROOT / "tests" / "_synthetic"; out = ROOT / "tests" / "_synthetic_out"
(data / "transcripts").mkdir(parents=True, exist_ok=True)
vids, bounds, queries = [], [], []
for v in range(4):
    vid = f"SYN{v}"; vids.append({"video_id": vid, "title": vid, "url": "", "subject": "syn", "licence": "syn",
                                  "split": "dev" if v < 2 else "test"})
    lines, t, topics = [], 0.0, ["alpha", "beta", "gamma"]
    for ti, topic in enumerate(topics):
        if ti > 0:
            bounds.append({"video_id": vid, "boundary_time_sec": round(t, 1)})
        start_t = t
        for _ in range(30):
            words = [random.choice(pools[topic]) if random.random() < .8 else random.choice(common) for _ in range(9)]
            lines.append({"text": " ".join(words), "start": round(t, 2), "duration": 5.0}); t += 4.0
        queries.append({"video_id": vid, "question": " ".join(pools[topic][:6]),
                        "answer_start_sec": round(start_t + 10, 1), "answer_end_sec": round(t - 10, 1)})
    (data / "transcripts" / f"{vid}.json").write_text(json.dumps(lines))
for name, rows in (("videos.csv", vids), ("boundaries_final.csv", bounds), ("queries.csv", queries)):
    with open(data / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

res = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_experiment.py"), "--fake-embedder",
                      "--data-dir", str(data), "--out-dir", str(out), "--config", str(ROOT / "config.json")],
                     capture_output=True, text=True)
print(res.stdout, res.stderr)
assert res.returncode == 0, "run_experiment failed"
assert (out / "report.md").exists() and (out / "test_per_video.csv").exists()
print("smoke test passed (synthetic data: results are NOT meaningful)")
