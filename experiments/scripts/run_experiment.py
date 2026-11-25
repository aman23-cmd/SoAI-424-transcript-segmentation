"""Runs the full experiment from the Final Team Version of the methodology.

1. choose the semantic threshold on the DEVELOPMENT videos (grid in config.json)
2. compute the baseline window W from the semantic segments on the development videos
3. choose the baseline window on the development videos from {100, W, 250}
4. run both methods ONCE on the TEST videos with the frozen settings
5. write per-video results, summaries, paired comparison, length distributions, manifest, report

Usage:  python scripts/run_experiment.py            (real embeddings)
        python scripts/run_experiment.py --fake-embedder --data-dir tests/_synthetic --out-dir tests/_synthetic_out
"""
import argparse
import csv
import hashlib
import json
import platform
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.embedding import Embedder, HashingEmbedder
from src.metrics import (WordTimeline, boundary_prf, length_distribution, mrr, pk_windowdiff,
                         random_reference, recall_at_k, retrieval_ranks, window_k)
from src.segmentation import fixed_segment, group_into_chunks, segment_embeddings, semantic_segment
from src.transcript import load_transcript

METRICS = ["boundary_f1", "boundary_precision", "boundary_recall", "pk", "windowdiff",
           "recall@1", "recall@3", "mrr", "n_segments", "mean_segment_words"]
HIGHER_IS_BETTER = {"boundary_f1": True, "boundary_precision": True, "boundary_recall": True,
                    "pk": False, "windowdiff": False, "recall@1": True, "recall@3": True,
                    "mrr": True}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ------------------------------------------------------------------ data
def load_data(data_dir):
    d = Path(data_dir)
    videos = [v for v in read_csv(d / "videos.csv") if v["video_id"].strip()]
    ref = defaultdict(list)
    for r in read_csv(d / "boundaries_final.csv"):
        ref[r["video_id"]].append(float(r["boundary_time_sec"]))
    qs = defaultdict(list)
    for r in read_csv(d / "queries.csv"):
        qs[r["video_id"]].append((r["question"], float(r["answer_start_sec"]), float(r["answer_end_sec"])))
    return videos, ref, qs


def prepare(video, ref, qs, data_dir, embedder, cfg):
    vid = video["video_id"]
    lines = load_transcript(vid, Path(data_dir) / "transcripts")
    chunks = group_into_chunks(lines, cfg["chunk_lines"])
    chunk_emb = embedder.encode([c["text"] for c in chunks])
    questions = qs[vid]
    return {
        "video_id": vid, "split": video["split"].strip().lower(),
        "lines": lines, "chunks": chunks, "chunk_emb": chunk_emb,
        "timeline": WordTimeline(lines), "ref_bounds": sorted(ref[vid]),
        "query_emb": embedder.encode([q[0] for q in questions]),
        "answers": [(q[1], q[2]) for q in questions],
    }


# ------------------------------------------------------------------ one method on one video
def segment(p, method, param, cfg):
    if method == "semantic":
        s = cfg["semantic"]
        return semantic_segment(p["chunks"], p["chunk_emb"], param, s["min_words"], s["max_words"])
    return fixed_segment(p["chunks"], int(param))


def evaluate_video(p, segs, cfg):
    tol, ks = cfg["boundary_tolerance_sec"], cfg["recall_k"]
    starts = [s["start"] for s in segs]
    pred_b = starts[1:]
    prec, rec, f1 = boundary_prf(p["ref_bounds"], pred_b, tol)
    tl = p["timeline"]
    ref_w = [tl.position(t) for t in p["ref_bounds"]]
    pred_w = [tl.position(t) for t in pred_b]
    k = window_k(ref_w, tl.total_words)
    pk, wd = pk_windowdiff(ref_w, pred_w, tl.total_words, k)
    ranks = retrieval_ranks(p["query_emb"], segment_embeddings(segs, p["chunk_emb"]), starts, p["answers"])
    res = {"video_id": p["video_id"], "boundary_precision": prec, "boundary_recall": rec,
           "boundary_f1": f1, "pk": pk, "windowdiff": wd, "window_k_words": k,
           "mrr": mrr(ranks), "n_segments": len(segs), "n_queries": len(ranks),
           "mean_segment_words": float(np.mean([s["words"] for s in segs]))}
    for kk in ks:
        res[f"recall@{kk}"] = recall_at_k(ranks, kk)
    res.update(random_reference(len(segs), ks))
    return res


def mean_over(preps, method, param, cfg):
    rows = [evaluate_video(p, segment(p, method, param, cfg), cfg) for p in preps]
    return rows, {m: float(np.nanmean([r[m] for r in rows])) for m in ["boundary_f1", "mrr"]}


def choose(grid_results):
    """Highest mean of (Boundary F1, MRR); ties broken by higher MRR."""
    def key(item):
        _, r = item
        return (round((r["boundary_f1"] + r["mrr"]) / 2, 10), round(r["mrr"], 10))
    return max(grid_results.items(), key=key)[0]


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--fake-embedder", action="store_true", help="smoke test only; never for reported results")
    ap.add_argument("--baseline-window", type=int, default=None,
                    help="sensitivity run only: override the dev-chosen fixed window")
    a = ap.parse_args()

    cfg = json.loads(Path(a.config).read_text())
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    embedder = HashingEmbedder() if a.fake_embedder else Embedder(cfg["embedding_model"])

    videos, ref, qs = load_data(a.data_dir)
    preps = [prepare(v, ref, qs, a.data_dir, embedder, cfg) for v in videos]
    dev = [p for p in preps if p["split"] == "dev"]
    test = [p for p in preps if p["split"] == "test"]
    if not dev or not test:
        sys.exit("Need at least one dev and one test video in data/videos.csv (split column).")
    for p in preps:
        if not p["answers"]:
            sys.exit(f"No queries for {p['video_id']}")
        if not p["ref_bounds"]:
            print(f"WARNING: no reference boundaries for {p['video_id']}")

    # 1. semantic threshold on dev videos
    sem_grid = {}
    dev_rows = []
    for thr in cfg["semantic"]["threshold_grid"]:
        rows, summ = mean_over(dev, "semantic", thr, cfg)
        sem_grid[thr] = summ
        dev_rows += [{"method": "semantic", "setting": thr, **r} for r in rows]
    best_thr = choose(sem_grid)

    # 2. baseline W from semantic segments on dev videos (pooled mean segment length in words)
    segs = [s for p in dev for s in segment(p, "semantic", best_thr, cfg)]
    W = int(round(sum(s["words"] for s in segs) / len(segs)))

    # 3. baseline window on dev videos
    windows = sorted(set([cfg["baseline"]["fixed_window_grid_extra"][0], W,
                          cfg["baseline"]["fixed_window_grid_extra"][1]]))
    fix_grid = {}
    for w in windows:
        rows, summ = mean_over(dev, "fixed", w, cfg)
        fix_grid[w] = summ
        dev_rows += [{"method": "fixed", "setting": w, **r} for r in rows]
    best_w = choose(fix_grid)
    if a.baseline_window:
        best_w = a.baseline_window

    # 4. test, once, frozen settings
    test_rows = []
    lengths = {"semantic": {"words": [], "seconds": []}, "fixed": {"words": [], "seconds": []}}
    for method, param in (("semantic", best_thr), ("fixed", best_w)):
        for p in test:
            segs = segment(p, method, param, cfg)
            test_rows.append({"method": method, "setting": param, **evaluate_video(p, segs, cfg)})
            lengths[method]["words"] += [s["words"] for s in segs]
            lengths[method]["seconds"] += [s["end"] - s["start"] for s in segs]

    # ---- outputs
    def write_csv(name, rows):
        keys = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

    write_csv("dev_grid_per_video.csv", dev_rows)
    write_csv("test_per_video.csv", test_rows)

    by = {m: {r["video_id"]: r for r in test_rows if r["method"] == m} for m in ("semantic", "fixed")}
    summary, paired = [], []
    for m in ("semantic", "fixed"):
        row = {"method": m, "setting": best_thr if m == "semantic" else best_w, "n_videos": len(test)}
        for k in METRICS:
            v = [r[k] for r in by[m].values()]
            row[f"{k}_mean"] = float(np.nanmean(v)); row[f"{k}_std"] = float(np.nanstd(v, ddof=1)) if len(v) > 1 else float("nan")
        summary.append(row)
    for k in METRICS:
        d = [by["semantic"][v][k] - by["fixed"][v][k] for v in by["semantic"]]
        p_val = None
        try:
            from scipy.stats import wilcoxon
            p_val = float(wilcoxon(d).pvalue)
        except Exception:
            pass
        hib = HIGHER_IS_BETTER.get(k)
        wins = ties = losses = None
        if hib is not None:
            wins = sum((x > 0) == hib and x != 0 for x in d); ties = sum(x == 0 for x in d)
            losses = len(d) - wins - ties
        paired.append({"metric": k, "mean_diff_semantic_minus_fixed": float(np.nanmean(d)),
                       "wilcoxon_p": p_val, "semantic_better_videos": wins, "ties": ties, "fixed_better_videos": losses})
    write_csv("test_summary.csv", summary)
    write_csv("paired_comparison.csv", paired)
    write_csv("segment_lengths.csv", [{"method": m, "unit": u, **length_distribution(lengths[m][u])}
                                      for m in lengths for u in ("words", "seconds")])

    manifest = {
        "run_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "embedder": type(embedder).__name__, "smoke_test_only": bool(a.fake_embedder), "config": cfg,
        "chosen": {"semantic_threshold": best_thr, "baseline_W_from_dev": W, "baseline_window_grid": windows,
                   "baseline_window": best_w},
        "dev_grid": {"semantic": {str(k): v for k, v in sem_grid.items()}, "fixed": {str(k): v for k, v in fix_grid.items()}},
        "n_dev_videos": len(dev), "n_test_videos": len(test),
        "data_sha256": {n: sha256(Path(a.data_dir) / n) for n in ("videos.csv", "boundaries_final.csv", "queries.csv")},
    }
    manifest["sensitivity_override_window"] = a.baseline_window
    try:
        import sentence_transformers; manifest["sentence_transformers"] = sentence_transformers.__version__
    except Exception:
        pass
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    write_report(out, manifest, summary, paired, by, lengths)
    print(f"semantic threshold={best_thr}  baseline W={W}  baseline window={best_w}")
    print(f"results written to {out}/ (open report.md)")


def f(x, nd=3):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def write_report(out, man, summary, paired, by, lengths):
    L = ["# Results report (auto-generated)", ""]
    if man["smoke_test_only"]:
        L += ["**SMOKE TEST ONLY: synthetic data and a hashing embedder. Do not report these numbers.**", ""]
    ch = man["chosen"]
    L += [f"Run: {man['run_utc']}  |  dev videos: {man['n_dev_videos']}, test videos: {man['n_test_videos']}",
          f"Chosen on development videos: semantic threshold = {ch['semantic_threshold']}; baseline W = {ch['baseline_W_from_dev']} "
          f"(grid {ch['baseline_window_grid']}); baseline window = {ch['baseline_window']}.", "",
          "## Mean over test videos (± std)", "", "| Metric | Semantic | Fixed-length |", "|---|---|---|"]
    s, b = summary
    for k in METRICS:
        L.append(f"| {k} | {f(s[k+'_mean'])} ± {f(s[k+'_std'])} | {f(b[k+'_mean'])} ± {f(b[k+'_std'])} |")
    L += ["", "## Paired comparison (semantic minus fixed-length)", "",
          "| Metric | Mean diff | Wilcoxon p | Semantic better | Ties | Fixed better |", "|---|---|---|---|---|---|"]
    for r in paired:
        L.append(f"| {r['metric']} | {f(r['mean_diff_semantic_minus_fixed'])} | {f(r['wilcoxon_p'])} | "
                 f"{r['semantic_better_videos']} | {r['ties']} | {r['fixed_better_videos']} |")
    L += ["", "(For Pk and WindowDiff lower is better. With few videos treat p-values cautiously.)", "",
          "## Per-video results where the fixed-length method is equal or better", ""]
    any_row = False
    for v in by["semantic"]:
        a, c = by["semantic"][v], by["fixed"][v]
        notes = []
        for k in ("boundary_f1", "mrr", "recall@1", "recall@3", "pk", "windowdiff"):
            if (c[k] >= a[k]) if HIGHER_IS_BETTER[k] else (c[k] <= a[k]):
                notes.append(f"{k}: semantic {f(a[k])} vs fixed {f(c[k])}")
        if notes:
            any_row = True
            L.append(f"- **{v}**: " + "; ".join(notes))
    if not any_row:
        L.append("- none")
    L += ["", "## Segment lengths on test videos", "", "| Method | Unit | min | q1 | median | q3 | max | mean |", "|---|---|---|---|---|---|---|---|"]
    for m in lengths:
        for u in ("words", "seconds"):
            d = length_distribution(lengths[m][u])
            L.append(f"| {m} | {u} | " + " | ".join(f(d[x], 1) for x in ("min", "q1", "median", "q3", "max", "mean")) + " |")
    L += ["", "## Random-ranking reference (mean over test videos)", "", "| Method | Recall@1 | Recall@3 | MRR |", "|---|---|---|---|"]
    for m in by:
        rr = [by[m][v] for v in by[m]]
        L.append(f"| {m} | " + " | ".join(f(np.mean([r[k] for r in rr])) for k in ("random_recall@1", "random_recall@3", "random_mrr")) + " |")
    (out / "report.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()