import sqlite3
import statistics
from collections import Counter

from db import DB_PATH


def _mean(values):
    return round(statistics.mean(values), 4) if values else None


def _std(values):
    return round(statistics.stdev(values), 4) if len(values) > 1 else None


def _pct(part, whole):
    return round(100 * part / whole, 2) if whole else None


def _summarize(cur, videos):
    """Aggregates stats for a list of video_history rows (one mode)."""
    all_scores, all_durations, all_words, overlap_secs = [], [], [], []
    difficulty_counter = Counter()
    total_segments = notes_ok = quiz_ok = total_questions = 0
    adjacent_pairs = overlapping_pairs = 0
    per_video = []

    for v in videos:
        segs = cur.execute(
            "SELECT * FROM segments WHERE video_history_id = ? ORDER BY start_time",
            (v["id"],),
        ).fetchall()

        v_scores = []
        v_notes_ok = v_questions = 0

        for s in segs:
            total_segments += 1

            if s["relevance_score"] is not None:
                notes_ok += 1
                v_notes_ok += 1
                all_scores.append(s["relevance_score"])
                v_scores.append(s["relevance_score"])

            qs = cur.execute(
                "SELECT difficulty FROM quiz_questions WHERE segment_id = ?", (s["id"],)
            ).fetchall()
            if qs:
                quiz_ok += 1
            total_questions += len(qs)
            v_questions += len(qs)
            difficulty_counter.update(q["difficulty"] for q in qs)

            if s["start_time"] is not None and s["end_time"] is not None:
                all_durations.append(s["end_time"] - s["start_time"])
            if s["transcript_text"]:
                all_words.append(len(s["transcript_text"].split()))

        for a, b in zip(segs, segs[1:]):
            adjacent_pairs += 1
            overlap = a["end_time"] - b["start_time"]
            if overlap > 0:
                overlapping_pairs += 1
                overlap_secs.append(overlap)

        per_video.append({
            "video_history_id": v["id"],
            "video_id": v["video_id"],
            "segments": len(segs),
            "notes_success_pct": _pct(v_notes_ok, len(segs)),
            "relevance_mean": _mean(v_scores),
            "total_questions": v_questions,
        })

    return {
        "videos_processed": len(videos),
        "total_segments_evaluated": total_segments,
        "notes": {
            "success_rate_pct": _pct(notes_ok, total_segments),
            "relevance_mean": _mean(all_scores),
            "relevance_std": _std(all_scores),
            "relevance_min": round(min(all_scores), 4) if all_scores else None,
            "relevance_max": round(max(all_scores), 4) if all_scores else None,
        },
        "quiz": {
            "total_questions": total_questions,
            "segments_with_quiz_pct": _pct(quiz_ok, total_segments),
            "avg_questions_per_segment": round(total_questions / total_segments, 2) if total_segments else None,
            "difficulty_distribution": dict(difficulty_counter),
        },
        "segmentation": {
            "avg_segment_duration_sec": _mean(all_durations),
            "avg_segment_words": _mean(all_words),
            "adjacent_pairs": adjacent_pairs,
            "overlapping_pairs": overlapping_pairs,
            "overlap_pct": _pct(overlapping_pairs, adjacent_pairs),
            "avg_overlap_sec": _mean(overlap_secs),
        },
        "per_video": per_video,
    }


def _compare(semantic, baseline):
    """
    Paired comparison on videos processed in BOTH modes.
    If a video was run more than once in a mode, the latest run is used.
    """
    sem_by_video = {pv["video_id"]: pv for pv in semantic["per_video"]}
    base_by_video = {pv["video_id"]: pv for pv in baseline["per_video"]}

    rows = []
    for video_id in sem_by_video:
        if video_id not in base_by_video:
            continue
        s = sem_by_video[video_id]["relevance_mean"]
        b = base_by_video[video_id]["relevance_mean"]
        if s is None or b is None:
            continue
        rows.append({
            "video_id": video_id,
            "semantic_relevance": s,
            "baseline_relevance": b,
            "difference": round(s - b, 4),
        })

    diffs = [r["difference"] for r in rows]
    return {
        "videos_compared": len(rows),
        "mean_difference_semantic_minus_baseline": _mean(diffs),
        "videos_where_semantic_higher": sum(1 for d in diffs if d > 0),
        "per_video": rows,
    }


def get_evaluation_summary():
    """
    Returns stats separately for 'semantic' (our method) and 'baseline'
    (fixed-size windows), plus a paired comparison between them.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    all_videos = cur.execute("SELECT * FROM video_history ORDER BY id").fetchall()

    by_mode = {"semantic": [], "baseline": []}
    for v in all_videos:
        mode = v["mode"] or "semantic"
        by_mode.setdefault(mode, []).append(v)

    semantic = _summarize(cur, by_mode["semantic"])
    baseline = _summarize(cur, by_mode["baseline"])

    conn.close()

    return {
        "semantic": semantic,
        "baseline": baseline,
        "comparison": _compare(semantic, baseline),
    }