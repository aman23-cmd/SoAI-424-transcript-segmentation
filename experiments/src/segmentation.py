"""Semantic (proposed) and fixed-length (baseline) segmentation of caption lines.

Both methods start from the same 5-line chunks (methodology: 'identical chunks').
"""
import numpy as np


def group_into_chunks(lines, n=5):
    chunks = []
    for i in range(0, len(lines), n):
        g = lines[i:i + n]
        text = " ".join(l["text"].replace("\n", " ") for l in g)
        chunks.append({
            "id": len(chunks),
            "text": text,
            "start": g[0]["start"],
            "end": g[-1]["start"] + g[-1]["duration"],
            "words": len(text.split()),
        })
    return chunks


def _cos(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0


def _make_segments(groups, chunks):
    segs = []
    for ids in groups:
        text = " ".join(chunks[i]["text"] for i in ids)
        segs.append({
            "chunk_ids": ids,
            "start": chunks[ids[0]]["start"],
            "end": chunks[ids[-1]]["end"],
            "text": text,
            "words": len(text.split()),
        })
    # end time is clamped to the next segment's start (caption durations overlap)
    for i in range(len(segs) - 1):
        segs[i]["end"] = min(segs[i]["end"], segs[i + 1]["start"])
    return segs


def semantic_segment(chunks, chunk_emb, threshold, min_words=80, max_words=250):
    """Boundary when cosine(consecutive chunks) < threshold AND current segment >= min_words;
    a segment is also closed once it reaches max_words."""
    if not chunks:
        return []
    groups, cur, cur_words = [], [0], chunks[0]["words"]
    for i in range(1, len(chunks)):
        sim = _cos(chunk_emb[i - 1], chunk_emb[i])
        topic_changed = sim < threshold and cur_words >= min_words
        too_long = cur_words >= max_words
        if topic_changed or too_long:
            groups.append(cur)
            cur, cur_words = [i], chunks[i]["words"]
        else:
            cur.append(i)
            cur_words += chunks[i]["words"]
    groups.append(cur)
    return _make_segments(groups, chunks)


def fixed_segment(chunks, window_words):
    """Non-overlapping windows that close once they reach window_words (last one may be shorter)."""
    if not chunks:
        return []
    groups, cur, cur_words = [], [], 0
    for c in chunks:
        cur.append(c["id"])
        cur_words += c["words"]
        if cur_words >= window_words:
            groups.append(cur)
            cur, cur_words = [], 0
    if cur:
        groups.append(cur)
    return _make_segments(groups, chunks)


def segment_embeddings(segs, chunk_emb):
    """Segment embedding = mean of its chunks' (normalised) embeddings, re-normalised."""
    out = []
    for s in segs:
        v = np.mean(chunk_emb[s["chunk_ids"]], axis=0)
        n = np.linalg.norm(v)
        out.append(v / n if n > 0 else v)
    return np.asarray(out)
