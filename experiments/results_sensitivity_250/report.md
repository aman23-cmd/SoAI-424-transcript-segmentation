# Results report (auto-generated)

Run: 2026-11-25T20:55:29.279619+00:00  |  dev videos: 3, test videos: 7
Chosen on development videos: semantic threshold = 0.35; baseline W = 228 (grid [100, 228, 250]); baseline window = 250.

## Mean over test videos (± std)

| Metric | Semantic | Fixed-length |
|---|---|---|
| boundary_f1 | 0.384 ± 0.102 | 0.369 ± 0.114 |
| boundary_precision | 0.257 ± 0.076 | 0.277 ± 0.096 |
| boundary_recall | 0.783 ± 0.186 | 0.560 ± 0.138 |
| pk | 0.542 ± 0.013 | 0.546 ± 0.016 |
| windowdiff | 0.705 ± 0.071 | 0.572 ± 0.030 |
| recall@1 | 0.657 ± 0.151 | 0.657 ± 0.251 |
| recall@3 | 0.886 ± 0.157 | 0.886 ± 0.157 |
| mrr | 0.781 ± 0.103 | 0.781 ± 0.140 |
| n_segments | 20.571 ± 3.952 | 14.286 ± 2.563 |
| mean_segment_words | 179.812 ± 12.592 | 258.270 ± 9.336 |

## Paired comparison (semantic minus fixed-length)

| Metric | Mean diff | Wilcoxon p | Semantic better | Ties | Fixed better |
|---|---|---|---|---|---|
| boundary_f1 | 0.016 | 0.938 | 3 | 0 | 4 |
| boundary_precision | -0.020 | 0.578 | 2 | 0 | 5 |
| boundary_recall | 0.223 | 0.062 | 5 | 2 | 0 |
| pk | -0.004 | 0.812 | 3 | 2 | 2 |
| windowdiff | 0.134 | 0.016 | 0 | 0 | 7 |
| recall@1 | 0.000 | 0.938 | 2 | 2 | 3 |
| recall@3 | 0.000 | 1.000 | 0 | 7 | 0 |
| mrr | -0.001 | 1.000 | 2 | 1 | 4 |
| n_segments | 6.286 | 0.016 | None | None | None |
| mean_segment_words | -78.458 | 0.016 | None | None | None |

(For Pk and WindowDiff lower is better. With few videos treat p-values cautiously.)

## Per-video results where the fixed-length method is equal or better

- **_nmm0nZqIIY**: mrr: semantic 0.767 vs fixed 0.900; recall@1: semantic 0.600 vs fixed 0.800; recall@3: semantic 1.000 vs fixed 1.000; pk: semantic 0.546 vs fixed 0.546; windowdiff: semantic 0.817 vs fixed 0.627
- **JFuMei9Wwk4**: boundary_f1: semantic 0.333 vs fixed 0.462; recall@3: semantic 1.000 vs fixed 1.000; windowdiff: semantic 0.729 vs fixed 0.580
- **qp8u-frRAnU**: boundary_f1: semantic 0.357 vs fixed 0.364; mrr: semantic 0.720 vs fixed 0.720; recall@1: semantic 0.600 vs fixed 0.600; recall@3: semantic 0.800 vs fixed 0.800; windowdiff: semantic 0.599 vs fixed 0.567
- **4r_XR9fUPhQ**: boundary_f1: semantic 0.250 vs fixed 0.333; mrr: semantic 0.822 vs fixed 0.829; recall@1: semantic 0.800 vs fixed 0.800; recall@3: semantic 0.800 vs fixed 0.800; pk: semantic 0.558 vs fixed 0.552; windowdiff: semantic 0.666 vs fixed 0.571
- **SiBw7os-_zI**: mrr: semantic 0.590 vs fixed 0.654; recall@1: semantic 0.400 vs fixed 0.600; recall@3: semantic 0.600 vs fixed 0.600; pk: semantic 0.533 vs fixed 0.533; windowdiff: semantic 0.747 vs fixed 0.579
- **drQK8ciCAjY**: recall@3: semantic 1.000 vs fixed 1.000; pk: semantic 0.544 vs fixed 0.526; windowdiff: semantic 0.658 vs fixed 0.540
- **wbaEgUjQyZM**: boundary_f1: semantic 0.387 vs fixed 0.435; mrr: semantic 0.867 vs fixed 1.000; recall@1: semantic 0.800 vs fixed 1.000; recall@3: semantic 1.000 vs fixed 1.000; windowdiff: semantic 0.720 vs fixed 0.538

## Segment lengths on test videos

| Method | Unit | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|---|
| semantic | words | 15.0 | 111.0 | 164.0 | 260.0 | 308.0 | 179.5 |
| semantic | seconds | 5.0 | 43.0 | 64.5 | 93.7 | 161.0 | 67.5 |
| fixed | words | 47.0 | 257.0 | 266.0 | 273.0 | 308.0 | 258.4 |
| fixed | seconds | 18.9 | 90.0 | 101.9 | 109.9 | 149.0 | 97.3 |

## Random-ranking reference (mean over test videos)

| Method | Recall@1 | Recall@3 | MRR |
|---|---|---|---|
| semantic | 0.050 | 0.151 | 0.180 |
| fixed | 0.072 | 0.217 | 0.233 |