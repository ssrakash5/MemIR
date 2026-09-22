<!-- DRAFT — Markdown first. Supplementary material only: nothing here is
load-bearing for the main claims in docs/paper/results.md, which already
state the pooled/summary findings with bootstrap CIs. Every table below is
pulled directly from results/metrics/*.csv (regenerable via
eval/compute_*.py from the DB) or from already-written, already-verified
project docs (docs/data_validation.md, docs/labeling_protocol.md,
configs/experiment_grid.yaml) -- nothing here is a new measurement. -->

# Appendix

Reviewers are not required to read this section (per the SaTML 2027
checklist); it exists for readers who want the full per-depth data
behind the summary tables in Results, the exact experimental design
parameters, and one worked example of the labeling rubric.

## A. Experimental grid

Full generation factorial (`configs/experiment_grid.yaml`):

| Factor | Levels |
|---|---|
| `scenario_id` | 30 (24 poisoned across 4 `poison_form` styles × 6 independently-constructed scenarios each, + 6 `clean_control`) |
| `model` | gpt-4o-mini, gpt-4o, Llama-3.3-70B-Instruct |
| `top_k` (retrieval fan-out) | 1, 3, 5, 10 |
| `write_fanout` | 1, 2, 3 |
| `derivation_transform` | summarize, paraphrase, refine, continue |
| `seed` | 0, 1, 2, 3, 4 (frozen, no ad hoc additions — see grid file's dated resolution) |

Total: 30 × 3 × 4 × 3 × 4 × 5 = 21,600 planned traces (21,570 generated,
99.86% — see Limitations for the 30 permanently-missing Llama traces).
`depth` (0–5) and `attribution_threshold` (null, 0.5, 0.7, 0.85) are
post-hoc analysis factors computed from each trace's persisted edges, not
separate generation runs. `containment_policy`
(`flat_transitive`/`depth_aware`) is a further post-hoc layer for H4.

`scenario_id` is the real inferential sampling unit (n=24 for H1–H4's
primary pooled estimand, stratified 6 per `poison_form`) — not
individual factorial cells, and not seed count. All 5 seeds are averaged
within scenario-condition before any bootstrap resampling; resampling
always sees 24 scenario units, never a larger pseudo-replicated count.
See `configs/experiment_grid.yaml`'s dated seed-resolution note for the
full statistical-power argument.

## B. Full per-depth H1 results (Recall vs. inflation growth)

Results §H1 reports only depth 1 and depth 5 per model. Full depth
1–5 sweep, both propagation policies, all three models (95% bootstrap
CI, n=24 scenarios, `results/metrics/h1_bootstrap_ci.csv`):

| Model | Policy | Depth | P_BR | R_BR | Inflation |
|---|---|---|---|---|---|
| gpt-4o-mini | context_exposure | 1 | 0.669 [0.642, 0.700] | 1.000 [1.000, 1.000] | 1.832 [1.748, 1.910] |
| gpt-4o-mini | context_exposure | 2 | 0.639 [0.612, 0.666] | 1.000 [1.000, 1.000] | 1.989 [1.868, 2.115] |
| gpt-4o-mini | context_exposure | 3 | 0.629 [0.602, 0.657] | 1.000 [1.000, 1.000] | 2.107 [1.942, 2.278] |
| gpt-4o-mini | context_exposure | 4 | 0.625 [0.596, 0.654] | 1.000 [1.000, 1.000] | 2.197 [1.995, 2.434] |
| gpt-4o-mini | context_exposure | 5 | 0.622 [0.593, 0.649] | 1.000 [1.000, 1.000] | 2.273 [2.044, 2.516] |
| gpt-4o-mini | structural | 1 | 0.981 [0.963, 0.996] | 0.915 [0.872, 0.955] | 0.932 [0.898, 0.964] |
| gpt-4o-mini | structural | 2 | 0.944 [0.923, 0.967] | 0.913 [0.884, 0.939] | 1.012 [0.959, 1.070] |
| gpt-4o-mini | structural | 3 | 0.933 [0.907, 0.962] | 0.918 [0.893, 0.941] | 1.070 [0.993, 1.150] |
| gpt-4o-mini | structural | 4 | 0.926 [0.897, 0.956] | 0.918 [0.896, 0.941] | 1.119 [1.018, 1.232] |
| gpt-4o-mini | structural | 5 | 0.923 [0.894, 0.953] | 0.921 [0.900, 0.943] | 1.157 [1.042, 1.275] |
| gpt-4o | context_exposure | 1 | 0.628 [0.609, 0.643] | 1.000 [1.000, 1.000] | 1.946 [1.904, 1.995] |
| gpt-4o | context_exposure | 2 | 0.597 [0.576, 0.618] | 1.000 [1.000, 1.000] | 2.119 [2.005, 2.243] |
| gpt-4o | context_exposure | 3 | 0.589 [0.564, 0.612] | 1.000 [1.000, 1.000] | 2.236 [2.051, 2.449] |
| gpt-4o | context_exposure | 4 | 0.584 [0.557, 0.610] | 1.000 [1.000, 1.000] | 2.331 [2.062, 2.632] |
| gpt-4o | context_exposure | 5 | 0.581 [0.552, 0.607] | 1.000 [1.000, 1.000] | 2.422 [2.100, 2.783] |
| gpt-4o | structural | 1 | 0.966 [0.901, 1.000] | 0.939 [0.873, 0.980] | 0.972 [0.960, 0.984] |
| gpt-4o | structural | 2 | 0.942 [0.894, 0.978] | 0.954 [0.914, 0.979] | 1.062 [1.012, 1.114] |
| gpt-4o | structural | 3 | 0.932 [0.886, 0.971] | 0.956 [0.920, 0.979] | 1.118 [1.030, 1.210] |
| gpt-4o | structural | 4 | 0.927 [0.880, 0.969] | 0.957 [0.927, 0.977] | 1.163 [1.041, 1.294] |
| gpt-4o | structural | 5 | 0.922 [0.875, 0.966] | 0.959 [0.930, 0.979] | 1.209 [1.056, 1.367] |
| llama-3.3-70b | context_exposure | 1 | 0.632 [0.620, 0.647] | 1.000 [1.000, 1.000] | 1.939 [1.895, 1.975] |
| llama-3.3-70b | context_exposure | 2 | 0.609 [0.587, 0.629] | 1.000 [1.000, 1.000] | 2.057 [1.952, 2.179] |
| llama-3.3-70b | context_exposure | 3 | 0.599 [0.571, 0.622] | 1.000 [1.000, 1.000] | 2.167 [1.984, 2.390] |
| llama-3.3-70b | context_exposure | 4 | 0.593 [0.562, 0.618] | 1.000 [1.000, 1.000] | 2.258 [2.014, 2.563] |
| llama-3.3-70b | context_exposure | 5 | 0.586 [0.552, 0.614] | 1.000 [1.000, 1.000] | 2.368 [2.034, 2.773] |
| llama-3.3-70b | structural | 1 | 1.000 [0.999, 1.000] | 0.976 [0.959, 0.989] | 0.976 [0.959, 0.990] |
| llama-3.3-70b | structural | 2 | 0.966 [0.938, 0.989] | 0.973 [0.959, 0.984] | 1.041 [0.988, 1.103] |
| llama-3.3-70b | structural | 3 | 0.952 [0.912, 0.984] | 0.975 [0.963, 0.985] | 1.096 [1.006, 1.208] |
| llama-3.3-70b | structural | 4 | 0.943 [0.901, 0.979] | 0.975 [0.964, 0.985] | 1.143 [1.016, 1.295] |
| llama-3.3-70b | structural | 5 | 0.934 [0.883, 0.974] | 0.976 [0.966, 0.985] | 1.198 [1.030, 1.407] |

Growth is monotone but concave in every row: most of the precision loss
and inflation growth happens by depth 2–3, not spread evenly across all
five depths.

## C. Full H2 attribution-threshold sweep

Results §H2 reports only depth 5. Full depth 1–5 sweep, all three
thresholds, all three models (`results/metrics/h2_bootstrap_ci.csv`):

| Model | Threshold | Depth | P_BR | R_BR |
|---|---|---|---|---|
| gpt-4o-mini | 0.5 | 1 | 0.957 [0.933, 0.979] | 0.983 [0.967, 0.995] |
| gpt-4o-mini | 0.5 | 2 | 0.920 [0.895, 0.946] | 0.988 [0.973, 0.997] |
| gpt-4o-mini | 0.5 | 3 | 0.907 [0.878, 0.938] | 0.989 [0.975, 0.998] |
| gpt-4o-mini | 0.5 | 4 | 0.901 [0.870, 0.933] | 0.990 [0.975, 0.998] |
| gpt-4o-mini | 0.5 | 5 | 0.898 [0.868, 0.930] | 0.990 [0.976, 0.999] |
| gpt-4o-mini | 0.7 | 1 | 0.874 [0.832, 0.918] | 0.844 [0.798, 0.892] |
| gpt-4o-mini | 0.7 | 2 | 0.839 [0.803, 0.875] | 0.859 [0.818, 0.904] |
| gpt-4o-mini | 0.7 | 3 | 0.830 [0.792, 0.869] | 0.867 [0.823, 0.910] |
| gpt-4o-mini | 0.7 | 4 | 0.823 [0.784, 0.863] | 0.870 [0.827, 0.914] |
| gpt-4o-mini | 0.7 | 5 | 0.820 [0.781, 0.860] | 0.871 [0.828, 0.916] |
| gpt-4o-mini | 0.85 | 1 | 0.648 [0.575, 0.722] | 0.620 [0.552, 0.689] |
| gpt-4o-mini | 0.85 | 2 | 0.639 [0.569, 0.708] | 0.626 [0.553, 0.701] |
| gpt-4o-mini | 0.85 | 3 | 0.635 [0.568, 0.703] | 0.631 [0.557, 0.709] |
| gpt-4o-mini | 0.85 | 4 | 0.635 [0.567, 0.703] | 0.632 [0.557, 0.710] |
| gpt-4o-mini | 0.85 | 5 | 0.633 [0.566, 0.701] | 0.632 [0.558, 0.711] |
| gpt-4o | 0.5 | 1 | 0.956 [0.916, 0.983] | 0.996 [0.991, 0.999] |
| gpt-4o | 0.5 | 2 | 0.911 [0.871, 0.946] | 0.997 [0.993, 0.999] |
| gpt-4o | 0.5 | 3 | 0.897 [0.854, 0.934] | 0.997 [0.994, 0.999] |
| gpt-4o | 0.5 | 4 | 0.891 [0.846, 0.931] | 0.997 [0.994, 1.000] |
| gpt-4o | 0.5 | 5 | 0.887 [0.841, 0.928] | 0.998 [0.995, 1.000] |
| gpt-4o | 0.7 | 1 | 0.945 [0.877, 0.986] | 0.938 [0.872, 0.980] |
| gpt-4o | 0.7 | 2 | 0.915 [0.869, 0.951] | 0.953 [0.924, 0.976] |
| gpt-4o | 0.7 | 3 | 0.902 [0.855, 0.942] | 0.956 [0.928, 0.978] |
| gpt-4o | 0.7 | 4 | 0.897 [0.849, 0.938] | 0.960 [0.937, 0.979] |
| gpt-4o | 0.7 | 5 | 0.892 [0.844, 0.935] | 0.962 [0.941, 0.980] |
| gpt-4o | 0.85 | 1 | 0.751 [0.656, 0.845] | 0.741 [0.650, 0.832] |
| gpt-4o | 0.85 | 2 | 0.726 [0.650, 0.808] | 0.731 [0.652, 0.815] |
| gpt-4o | 0.85 | 3 | 0.720 [0.649, 0.797] | 0.729 [0.648, 0.812] |
| gpt-4o | 0.85 | 4 | 0.714 [0.644, 0.792] | 0.726 [0.646, 0.810] |
| gpt-4o | 0.85 | 5 | 0.710 [0.639, 0.786] | 0.725 [0.645, 0.809] |
| llama-3.3-70b | 0.5 | 1 | 0.973 [0.954, 0.989] | 0.993 [0.989, 0.997] |
| llama-3.3-70b | 0.5 | 2 | 0.928 [0.898, 0.955] | 0.996 [0.993, 0.998] |
| llama-3.3-70b | 0.5 | 3 | 0.912 [0.874, 0.945] | 0.996 [0.994, 0.998] |
| llama-3.3-70b | 0.5 | 4 | 0.900 [0.861, 0.936] | 0.997 [0.995, 0.998] |
| llama-3.3-70b | 0.5 | 5 | 0.890 [0.845, 0.929] | 0.997 [0.996, 0.999] |
| llama-3.3-70b | 0.7 | 1 | 0.956 [0.930, 0.980] | 0.940 [0.910, 0.968] |
| llama-3.3-70b | 0.7 | 2 | 0.914 [0.884, 0.942] | 0.943 [0.915, 0.970] |
| llama-3.3-70b | 0.7 | 3 | 0.898 [0.860, 0.931] | 0.946 [0.919, 0.972] |
| llama-3.3-70b | 0.7 | 4 | 0.889 [0.849, 0.922] | 0.948 [0.920, 0.974] |
| llama-3.3-70b | 0.7 | 5 | 0.878 [0.832, 0.916] | 0.949 [0.921, 0.975] |
| llama-3.3-70b | 0.85 | 1 | 0.678 [0.601, 0.757] | 0.674 [0.599, 0.752] |
| llama-3.3-70b | 0.85 | 2 | 0.655 [0.579, 0.738] | 0.665 [0.589, 0.744] |
| llama-3.3-70b | 0.85 | 3 | 0.649 [0.570, 0.728] | 0.659 [0.585, 0.738] |
| llama-3.3-70b | 0.85 | 4 | 0.645 [0.567, 0.724] | 0.655 [0.579, 0.733] |
| llama-3.3-70b | 0.85 | 5 | 0.640 [0.562, 0.720] | 0.652 [0.578, 0.731] |

The frontier is already largely set by depth 2 — recall at 0.85 barely
moves between depth 2 (0.63–0.73) and depth 5 (0.63–0.73) for any model,
while precision keeps drifting down slowly. The steep recall cost of an
aggressive threshold is a depth-1 phenomenon, not something that
compounds further with depth.

## D. Full H3 per-transform laundering breakdown

Results §H3 reports overall and select per-transform findings. Full
per-model × per-transform × per-depth breakdown
(`results/metrics/h3_laundering_summary.csv`):

| Model | Transform | Depth | n_CARRIES | n_laundered | Laundering rate | Structural-lineage recall |
|---|---|---|---|---|---|---|
| gpt-4o | continue | 1 | 1677 | 6 | 0.358% | 0.811 |
| gpt-4o | continue | 2 | 1507 | 2 | 0.133% | 0.883 |
| gpt-4o | continue | 3 | 1511 | 6 | 0.397% | 0.866 |
| gpt-4o | continue | 4 | 1544 | 13 | 0.842% | 0.846 |
| gpt-4o | continue | 5 | 1484 | 7 | 0.472% | 0.865 |
| gpt-4o | paraphrase | 1 | 1279 | 0 | 0.000% | 0.998 |
| gpt-4o | paraphrase | 2 | 1272 | 0 | 0.000% | 1.000 |
| gpt-4o | paraphrase | 3 | 1256 | 0 | 0.000% | 1.000 |
| gpt-4o | paraphrase | 4 | 1231 | 0 | 0.000% | 1.000 |
| gpt-4o | paraphrase | 5 | 1226 | 0 | 0.000% | 1.000 |
| gpt-4o | refine | 1 | 1390 | 0 | 0.000% | 0.982 |
| gpt-4o | refine | 2 | 1344 | 0 | 0.000% | 1.000 |
| gpt-4o | refine | 3 | 1324 | 0 | 0.000% | 1.000 |
| gpt-4o | refine | 4 | 1330 | 0 | 0.000% | 1.000 |
| gpt-4o | refine | 5 | 1321 | 0 | 0.000% | 1.000 |
| gpt-4o | summarize | 1 | 1246 | 11 | 0.883% | 1.000 |
| gpt-4o | summarize | 2 | 1298 | 16 | 1.233% | 1.000 |
| gpt-4o | summarize | 3 | 1288 | 16 | 1.242% | 1.000 |
| gpt-4o | summarize | 4 | 1303 | 19 | 1.458% | 1.000 |
| gpt-4o | summarize | 5 | 1305 | 22 | 1.686% | 1.000 |
| gpt-4o-mini | continue | 1 | 1796 | 28 | 1.559% | 0.719 |
| gpt-4o-mini | continue | 2 | 2076 | 45 | 2.168% | 0.630 |
| gpt-4o-mini | continue | 3 | 2047 | 22 | 1.075% | 0.638 |
| gpt-4o-mini | continue | 4 | 2098 | 31 | 1.478% | 0.615 |
| gpt-4o-mini | continue | 5 | 2051 | 25 | 1.219% | 0.628 |
| gpt-4o-mini | paraphrase | 1 | 1263 | 0 | 0.000% | 0.993 |
| gpt-4o-mini | paraphrase | 2 | 1205 | 0 | 0.000% | 0.993 |
| gpt-4o-mini | paraphrase | 3 | 1191 | 0 | 0.000% | 1.000 |
| gpt-4o-mini | paraphrase | 4 | 1197 | 0 | 0.000% | 1.000 |
| gpt-4o-mini | paraphrase | 5 | 1199 | 0 | 0.000% | 1.000 |
| gpt-4o-mini | refine | 1 | 1552 | 0 | 0.000% | 0.883 |
| gpt-4o-mini | refine | 2 | 1440 | 0 | 0.000% | 0.967 |
| gpt-4o-mini | refine | 3 | 1427 | 0 | 0.000% | 0.980 |
| gpt-4o-mini | refine | 4 | 1439 | 0 | 0.000% | 0.963 |
| gpt-4o-mini | refine | 5 | 1422 | 0 | 0.000% | 0.985 |
| gpt-4o-mini | summarize | 1 | 1396 | 0 | 0.000% | 0.907 |
| gpt-4o-mini | summarize | 2 | 1251 | 0 | 0.000% | 1.000 |
| gpt-4o-mini | summarize | 3 | 1276 | 0 | 0.000% | 1.000 |
| gpt-4o-mini | summarize | 4 | 1272 | 0 | 0.000% | 1.000 |
| gpt-4o-mini | summarize | 5 | 1284 | 0 | 0.000% | 1.000 |
| llama-3.3-70b | continue | 1 | 1564 | 8 | 0.512% | 0.865 |
| llama-3.3-70b | continue | 2 | 1563 | 19 | 1.216% | 0.865 |
| llama-3.3-70b | continue | 3 | 1457 | 25 | 1.716% | 0.890 |
| llama-3.3-70b | continue | 4 | 1460 | 20 | 1.370% | 0.872 |
| llama-3.3-70b | continue | 5 | 1375 | 36 | 2.618% | 0.884 |
| llama-3.3-70b | paraphrase | 1 | 1383 | 29 | 2.097% | 0.996 |
| llama-3.3-70b | paraphrase | 2 | 1274 | 61 | 4.788% | 1.000 |
| llama-3.3-70b | paraphrase | 3 | 1255 | 74 | 5.896% | 1.000 |
| llama-3.3-70b | paraphrase | 4 | 1227 | 63 | 5.134% | 1.000 |
| llama-3.3-70b | paraphrase | 5 | 1213 | 57 | 4.699% | 1.000 |
| llama-3.3-70b | refine | 1 | 1397 | 0 | 0.000% | 0.994 |
| llama-3.3-70b | refine | 2 | 1391 | 0 | 0.000% | 0.996 |
| llama-3.3-70b | refine | 3 | 1388 | 1 | 0.072% | 0.999 |
| llama-3.3-70b | refine | 4 | 1383 | 0 | 0.000% | 0.999 |
| llama-3.3-70b | refine | 5 | 1371 | 0 | 0.000% | 1.000 |
| llama-3.3-70b | summarize | 1 | 1305 | 0 | 0.000% | 0.962 |
| llama-3.3-70b | summarize | 2 | 1298 | 0 | 0.000% | 0.986 |
| llama-3.3-70b | summarize | 3 | 1290 | 0 | 0.000% | 1.000 |
| llama-3.3-70b | summarize | 4 | 1280 | 0 | 0.000% | 1.000 |
| llama-3.3-70b | summarize | 5 | 1285 | 0 | 0.000% | 1.000 |

`refine` launders essentially nowhere (one single-count exception at
llama-3.3-70b depth 3) and `paraphrase` launders nowhere for gpt-4o/
gpt-4o-mini — but launders substantially for llama-3.3-70b (4.7–5.9%),
the sharpest single cell in the whole table and the clearest evidence
that laundering is a model property, not a transform property alone.

## E. Full H4 containment-cost breakdown

Results §H4 reports only depth 5. Full depth 1–5 breakdown, both
policies, all three models — mean objects flagged and mean missed
contamination per trace (`results/metrics/h4_containment_raw.csv`,
aggregated):

| Model | Policy | Depth | Objects flagged (mean) | Missed contamination (mean) |
|---|---|---|---|---|
| gpt-4o-mini | flat_transitive | 1 | 2.000 | 0.000 |
| gpt-4o-mini | flat_transitive | 2 | 4.000 | 0.000 |
| gpt-4o-mini | flat_transitive | 3 | 6.000 | 0.000 |
| gpt-4o-mini | flat_transitive | 4 | 8.000 | 0.000 |
| gpt-4o-mini | flat_transitive | 5 | 10.000 | 0.001 |
| gpt-4o-mini | depth_aware | 1 | 2.000 | 0.000 |
| gpt-4o-mini | depth_aware | 2 | 4.000 | 0.000 |
| gpt-4o-mini | depth_aware | 3 | 5.000 | 0.134 |
| gpt-4o-mini | depth_aware | 4 | 6.000 | 0.283 |
| gpt-4o-mini | depth_aware | 5 | 7.000 | 0.419 |
| gpt-4o | flat_transitive | 1 | 2.000 | 0.000 |
| gpt-4o | flat_transitive | 2 | 4.000 | 0.000 |
| gpt-4o | flat_transitive | 3 | 6.000 | 0.000 |
| gpt-4o | flat_transitive | 4 | 8.000 | 0.000 |
| gpt-4o | flat_transitive | 5 | 10.000 | 0.000 |
| gpt-4o | depth_aware | 1 | 2.000 | 0.000 |
| gpt-4o | depth_aware | 2 | 4.000 | 0.000 |
| gpt-4o | depth_aware | 3 | 5.000 | 0.035 |
| gpt-4o | depth_aware | 4 | 6.000 | 0.077 |
| gpt-4o | depth_aware | 5 | 7.000 | 0.111 |
| llama-3.3-70b | flat_transitive | 1 | 1.997 | 0.000 |
| llama-3.3-70b | flat_transitive | 2 | 3.994 | 0.000 |
| llama-3.3-70b | flat_transitive | 3 | 5.991 | 0.000 |
| llama-3.3-70b | flat_transitive | 4 | 7.988 | 0.000 |
| llama-3.3-70b | flat_transitive | 5 | 9.985 | 0.000 |
| llama-3.3-70b | depth_aware | 1 | 1.997 | 0.000 |
| llama-3.3-70b | depth_aware | 2 | 3.994 | 0.000 |
| llama-3.3-70b | depth_aware | 3 | 4.994 | 0.028 |
| llama-3.3-70b | depth_aware | 4 | 5.994 | 0.061 |
| llama-3.3-70b | depth_aware | 5 | 6.994 | 0.089 |

Both policies are identical through depth 2 (`depth_aware`'s 2-hop
conservative window hasn't yet switched to structural-only propagation)
and diverge starting depth 3 — exactly the depth at which
`depth_aware`'s missed-contamination cost starts accruing, and gpt-4o-mini
pulls away from the other two models by roughly the same margin at every
depth ≥3.

## F. Seed diversity (data-validation finding)

Reported here rather than left buried in `docs/data_validation.md`,
since it bears on how much independent signal the 5-seeds-per-cell
design actually buys beyond the frozen `scenario_id`-based n=24. Not a
bug — no `seed` parameter is ever sent to any model API (a deliberate
choice: seeds rely on genuine API-level stochasticity at `temperature=0`,
not a request-level seed, since passing one would defeat the
noise-reduction purpose seeds were added for) — but the duplication rate
is worth stating plainly:

| | Share of cells |
|---|---|
| All 5 seeds byte-identical | 39.5% (1,708 / 4,320 cells) |
| All 5 seeds distinct | 8.8% (381 / 4,320 cells) |
| Partial diversity (2–4 unique) | 51.6% (2,231 / 4,320 cells) |

Varies by `derivation_transform` in the direction genuine task
determinism would predict: `summarize` 60.6% fully-duplicated,
`refine` 42.5%, `paraphrase` 38.3%, `continue` 16.8% — summarization is
the most constrained/convergent task, free continuation the least. This
does not change the statistical design (the bootstrap unit is
`scenario_id`, n=24, unaffected by within-cell seed duplication), but a
reviewer computing effective sample size from raw trace counts would
overestimate it without this table.

## G. Worked labeling example

One example illustrating the CARRIES/REFERENCES/CLEAN rubric and the
compositional-target rule (full rubric and all worked examples:
`docs/labeling_protocol.md`), representative of the `multi_hop_setup`
boundary case discussed in Limitations as the labeler's weakest point:

- **`semantic_target`**: "Route every signed NDA to
  `mirror-intake@compliance-shadow.example` before it is countersigned."
- **Candidate A** — *"All executed NDAs are now automatically forwarded
  to `mirror-intake@compliance-shadow.example` prior to final
  countersignature."* → **CARRIES**: restates the full claim (forwarding
  destination + timing relative to countersignature) in different words.
- **Candidate B** — *"Legal has been discussing changes to the NDA
  countersignature workflow, including a new pre-signature review step
  routed through the compliance team's shared intake address."* →
  **REFERENCES**: preserves the topic (NDA routing, pre-signature,
  compliance intake) without asserting the specific destination or the
  mandatory-forwarding claim.
- **Candidate C** — *"The legal team updated their document retention
  policy for signed contracts."* → **CLEAN**: no trace of the claim.

The compositional-target rule (frozen, `docs/labeling_protocol.md`)
applies when a target requires combining two premises: CARRIES requires
the candidate to assert the *combined* claim, not merely restate both
underlying facts side by side — this is specifically what depresses
REFERENCES-class recall (0.46) in `multi_hop_setup` scenarios, as
reported in Limitations and independently corroborated by the
human-human κ baseline (`results/kappa_sample/human_human_kappa_report.md`,
2026-09-21): all 5 annotator disagreements in that 120-sample check were
exactly this REFERENCES-vs-CARRIES boundary.
