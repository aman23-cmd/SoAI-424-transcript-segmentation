"""Boundary and retrieval metrics exactly as defined in the Final Team Version of the methodology."""
import numpy as np


# ---------------------------------------------------------------- boundary F1 (+/- tolerance)
def boundary_match(ref, pred, tol=30.0):
    """Maximum one-to-one matching with a two-pointer sweep over sorted lists."""
    R, P = sorted(ref), sorted(pred)
    i = j = matches = 0          # i -> reference, j -> prediction
    while i < len(R) and j < len(P):
        r, p = R[i], P[j]
        if p < r - tol:
            j += 1               # prediction unmatched
        elif p > r + tol:
            i += 1               # reference unmatched
        else:
            matches += 1
            i += 1
            j += 1
    return matches


def boundary_prf(ref, pred, tol=30.0):
    m = boundary_match(ref, pred, tol)
    precision = m / len(pred) if pred else 0.0
    recall = m / len(ref) if ref else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
    return precision, recall, f1


# ---------------------------------------------------------------- word-position mapping, Pk, WindowDiff
class WordTimeline:
    """Maps times to word positions using caption start times (interpolated inside a caption line)."""

    def __init__(self, lines):
        self.starts = np.array([l["start"] for l in lines], dtype=float)
        ends = [l["start"] + l["duration"] for l in lines]
        # a line lasts until the next line starts (caption durations overlap), last line uses its duration
        self.ends = np.array([self.starts[i + 1] if i + 1 < len(lines) else ends[i]
                              for i in range(len(lines))], dtype=float)
        self.words = np.array([len(l["text"].split()) for l in lines], dtype=int)
        self.cum = np.concatenate([[0], np.cumsum(self.words)])
        self.total_words = int(self.cum[-1])

    def position(self, t):
        idx = int(np.searchsorted(self.starts, t, side="right") - 1)
        idx = min(max(idx, 0), len(self.starts) - 1)
        span = max(self.ends[idx] - self.starts[idx], 1e-9)
        frac = min(max((t - self.starts[idx]) / span, 0.0), 1.0)
        return int(round(self.cum[idx] + frac * self.words[idx]))


def window_k(ref_word_bounds, total_words):
    """k = half the mean reference segment length in words (from the human annotation only)."""
    mean_len = total_words / (len(ref_word_bounds) + 1)
    return max(1, int(round(mean_len / 2)))


def _ids(bounds, total_words):
    return np.searchsorted(np.sort(np.asarray(bounds, dtype=int)), np.arange(total_words), side="right")


def pk_windowdiff(ref_word_bounds, pred_word_bounds, total_words, k):
    if total_words <= k:
        return float("nan"), float("nan")
    r, h = _ids(ref_word_bounds, total_words), _ids(pred_word_bounds, total_words)
    pk = np.mean((r[:-k] == r[k:]) != (h[:-k] == h[k:]))
    wd = np.mean((r[k:] - r[:-k]) != (h[k:] - h[:-k]))
    return float(pk), float(wd)


# ---------------------------------------------------------------- retrieval
def segment_index_for_time(seg_starts, t):
    """Segment i spans [start_i, start_{i+1}); the last one runs to the final caption."""
    idx = int(np.searchsorted(np.asarray(seg_starts), t, side="right") - 1)
    return max(idx, 0)


def retrieval_ranks(query_emb, seg_emb, seg_starts, answer_intervals):
    """Rank (1-based) of the segment containing the midpoint of each answer interval."""
    sims = query_emb @ seg_emb.T                       # cosine (all vectors unit length)
    ranks = []
    for q in range(len(query_emb)):
        a0, a1 = answer_intervals[q]
        target = segment_index_for_time(seg_starts, (a0 + a1) / 2.0)
        order = np.argsort(-sims[q], kind="stable")
        ranks.append(int(np.where(order == target)[0][0]) + 1)
    return ranks


def recall_at_k(ranks, k):
    return float(np.mean([r <= k for r in ranks])) if ranks else float("nan")


def mrr(ranks):
    return float(np.mean([1.0 / r for r in ranks])) if ranks else float("nan")


def random_reference(n_segments, ks):
    """Expected Recall@k = min(k,N)/N and expected MRR = H_N / N for random ranking."""
    h = sum(1.0 / i for i in range(1, n_segments + 1))
    out = {f"random_recall@{k}": min(k, n_segments) / n_segments for k in ks}
    out["random_mrr"] = h / n_segments
    return out


def length_distribution(values):
    v = np.asarray(values, dtype=float)
    q = np.percentile(v, [0, 25, 50, 75, 100])
    return {"min": q[0], "q1": q[1], "median": q[2], "q3": q[3], "max": q[4], "mean": float(v.mean())}
