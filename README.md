# Semantic vs fixed-length transcript segmentation for timestamp-aware retrieval (SoAI-424)

Team: Aman Kaushal, Vedant Kasaudhan. Guide: Bipul Shahi. This repository holds the code, settings, run instructions, video list and test files for the Final Team Version of the methodology.

**Question.** Does sentence-embedding semantic segmentation of captioned English lecture transcripts give more accurate topic boundaries and better timestamp retrieval than fixed-length segmentation? Notes and quiz generation (Gemini) are secondary features and are not part of this evaluation.

## Folder layout

| Path | Content |
|---|---|
| `config.json` | All settings (embedding model, chunk size, threshold grid, length limits, tolerance, k values) |
| `data/videos.csv` | Video list: `video_id, title, url, subject, licence, split (dev/test)` |
| `data/annotations.csv` | Independent boundary annotations (`annotator` = A1 or A2) |
| `data/boundaries_final.csv` | Agreed reference boundaries (frozen before any run) |
| `data/queries.csv` | Queries with answer intervals: `video_id, question, answer_start_sec, answer_end_sec` (frozen) |
| `data/transcripts/` | Downloaded transcripts (git-ignored, not redistributed) |
| `src/` | Segmentation (`segmentation.py`), metrics (`metrics.py`), embeddings, transcript download |
| `scripts/` | `fetch_transcripts.py`, `agreement.py`, `run_experiment.py` |
| `tests/smoke_test.py` | Runs the whole pipeline on synthetic data (checks the code only) |
| `results/` | Output of `run_experiment.py` (tables, manifest, `report.md`) |

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python tests/smoke_test.py   # should end with "smoke test passed"
```

Tested with Python 3.13. The smoke test uses a hashing embedder and synthetic data; its numbers are meaningless.

## Run instructions (in this order)

1. **Videos.** Fill `data/videos.csv` (10 videos; first 3 `dev`, other 7 `test`; record the licence).
2. **Transcripts.** `python scripts/fetch_transcripts.py` (needs internet; videos that fail are excluded and documented).
3. **Annotation.** Before running any method, A1 and A2 independently fill `data/annotations.csv` (topic-change times in seconds) from the video and the timestamped transcript, without seeing any method output.
4. **Agreement.** `python scripts/agreement.py` prints Boundary F1 (+/-30 s) and Pk between A1 and A2 and writes `data/boundaries_merged_draft.csv` (boundaries both marked) and `data/boundaries_to_discuss.csv` (single-annotator boundaries). After discussion write the agreed boundaries to `data/boundaries_final.csv`.
5. **Queries.** Write 5 questions per video in `data/queries.csv` with the answer start and end second. Settle disagreements by discussion; count discarded queries.
6. **Freeze.** Record date, time and SHA-256 of `boundaries_final.csv` and `queries.csv` (the manifest also stores the hashes). Do not edit them afterwards.
7. **Run.** `python scripts/run_experiment.py`
8. **Read results.** `results/report.md` (tables), `results/test_per_video.csv`, `results/paired_comparison.csv`, `results/segment_lengths.csv`, `results/run_manifest.json`.

## What `run_experiment.py` does

1. Chooses the semantic threshold from {0.35, 0.45, 0.55} on the **development** videos.
2. Computes the baseline window W = pooled mean segment length (words) of the semantic segments on the development videos, rounded.
3. Chooses the baseline window from {100, W, 250} on the development videos.
4. Selection rule for both methods: highest mean of Boundary F1 and MRR (ties: higher MRR).
5. Runs both methods **once** on the **test** videos with the frozen settings, on identical transcripts and identical 5-line chunks.

## Settings and definitions

- Chunks: 5 consecutive caption lines. Embedding model: `all-MiniLM-L6-v2`.
- Semantic: boundary when cosine similarity of consecutive chunks < threshold and the segment has >= 80 words; segment also closed at 250 words; segment end clamped to next start.
- Fixed-length: non-overlapping windows closing at W words.
- Boundary F1: one-to-one matching within +/-30 s (two-pointer sweep). Predicted boundaries are the start times of all segments except the first.
- Pk and WindowDiff: on transcript words; k = half the mean reference segment length (from the human annotation only), same k for both methods.
- Retrieval: segment embedding = mean of its chunk embeddings; segments ranked by cosine similarity to the query; a hit means the midpoint of the annotated answer interval lies in the returned segment (segment i spans [start_i, start_{i+1})). Recall@1, Recall@3, MRR (rank among all segments of the video). Random-ranking references and segment-length distributions are reported.
- Paired comparison: per-video differences, Wilcoxon signed-rank test (interpret cautiously with few videos). Cases where the fixed-length method is equal or better are listed in `report.md`.

## Reproducibility

Segmentation is deterministic and involves no training. Settings are in `config.json`; the run manifest stores chosen settings, library versions, data hashes and the run time. Transcripts are not redistributed: video IDs and the scripts above are enough to rebuild them. Gemini notes and quizzes (not in this repository) can vary between runs.

## Limitations

The annotators are also the developers (blinding to method output and freezing the annotations before any run reduce this bias). The sample is small (10 videos, 7 test), so no claim beyond this sample is made.
