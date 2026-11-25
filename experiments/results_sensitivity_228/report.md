# Results report (auto-generated)

Run: 2026-11-25T20:54:36.926921+00:00  |  dev videos: 3, test videos: 7
Chosen on development videos: semantic threshold = 0.35; baseline W = 228 (grid [100, 228, 250]); baseline window = 228.

## Mean over test videos (± std)

| Metric | Semantic | Fixed-length |
|---|---|---|
| boundary_f1 | 0.384 ± 0.102 | 0.383 ± 0.142 |
| boundary_precision | 0.257 ± 0.076 | 0.279 ± 0.113 |
| boundary_recall | 0.783 ± 0.186 | 0.617 ± 0.188 |
| pk | 0.542 ± 0.013 | 0.550 ± 0.016 |
| windowdiff | 0.705 ± 0.071 | 0.594 ± 0.051 |
| recall@1 | 0.657 ± 0.151 | 0.743 ± 0.223 |
| recall@3 | 0.886 ± 0.157 | 0.943 ± 0.098 |
| mrr | 0.781 ± 0.103 | 0.839 ± 0.139 |
| n_segments | 20.571 ± 3.952 | 15.429 ± 2.507 |
| mean_segment_words | 179.812 ± 12.592 | 238.533 ± 8.341 |

## Paired comparison (semantic minus fixed-length)

| Metric | Mean diff | Wilcoxon p | Semantic better | Ties | Fixed better |
|---|---|---|---|---|---|
| boundary_f1 | 0.002 | 0.938 | 4 | 0 | 3 |
| boundary_precision | -0.022 | 0.578 | 3 | 0 | 4 |
| boundary_recall | 0.166 | 0.156 | 5 | 1 | 1 |
| pk | -0.008 | 0.125 | 4 | 2 | 1 |
| windowdiff | 0.111 | 0.016 | 0 | 0 | 7 |
| recall@1 | -0.086 | 0.500 | 1 | 3 | 3 |
| recall@3 | -0.057 | 0.500 | 0 | 5 | 2 |
| mrr | -0.058 | 0.156 | 1 | 1 | 5 |
| n_segments | 5.143 | 0.016 | None | None | None |
| mean_segment_words | -58.721 | 0.016 | None | None | None |

(For Pk and WindowDiff lower is better. With few videos treat p-values cautiously.)

## Per-video results where the fixed-length method is equal or better

- **_nmm0nZqIIY**: recall@3: semantic 1.000 vs fixed 1.000; pk: semantic 0.546 vs fixed 0.546; windowdiff: semantic 0.817 vs fixed 0.688
- **JFuMei9Wwk4**: mrr: semantic 0.900 vs fixed 1.000; recall@1: semantic 0.800 vs fixed 1.000; recall@3: semantic 1.000 vs fixed 1.000; windowdiff: semantic 0.729 vs fixed 0.590
- **qp8u-frRAnU**: mrr: semantic 0.720 vs fixed 0.720; recall@1: semantic 0.600 vs fixed 0.600; recall@3: semantic 0.800 vs fixed 0.800; windowdiff: semantic 0.599 vs fixed 0.556
- **4r_XR9fUPhQ**: boundary_f1: semantic 0.250 vs fixed 0.421; mrr: semantic 0.822 vs fixed 0.867; recall@1: semantic 0.800 vs fixed 0.800; recall@3: semantic 0.800 vs fixed 1.000; windowdiff: semantic 0.666 vs fixed 0.599
- **SiBw7os-_zI**: mrr: semantic 0.590 vs fixed 0.717; recall@1: semantic 0.400 vs fixed 0.600; recall@3: semantic 0.600 vs fixed 0.800; pk: semantic 0.533 vs fixed 0.533; windowdiff: semantic 0.747 vs fixed 0.625
- **drQK8ciCAjY**: boundary_f1: semantic 0.583 vs fixed 0.667; mrr: semantic 0.800 vs fixed 1.000; recall@1: semantic 0.600 vs fixed 1.000; recall@3: semantic 1.000 vs fixed 1.000; windowdiff: semantic 0.658 vs fixed 0.572
- **wbaEgUjQyZM**: boundary_f1: semantic 0.387 vs fixed 0.417; mrr: semantic 0.867 vs fixed 0.900; recall@1: semantic 0.800 vs fixed 0.800; recall@3: semantic 1.000 vs fixed 1.000; pk: semantic 0.528 vs fixed 0.526; windowdiff: semantic 0.720 vs fixed 0.530

## Segment lengths on test videos

| Method | Unit | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|---|
| semantic | words | 15.0 | 111.0 | 164.0 | 260.0 | 308.0 | 179.5 |
| semantic | seconds | 5.0 | 43.0 | 64.5 | 93.7 | 161.0 | 67.5 |
| fixed | words | 17.0 | 234.0 | 241.0 | 252.0 | 288.0 | 239.3 |
| fixed | seconds | 12.2 | 84.8 | 92.7 | 100.9 | 130.5 | 90.1 |

## Random-ranking reference (mean over test videos)

| Method | Recall@1 | Recall@3 | MRR |
|---|---|---|---|
| semantic | 0.050 | 0.151 | 0.180 |
| fixed | 0.066 | 0.199 | 0.220 |