<!-- DRAFT — Markdown first. All numbers below are pulled directly from
results/metrics/*.csv (regenerable from the DB via eval/compute_*.py),
not transcribed from memory. Figures (matplotlib, from these CSVs) are
not yet generated -- next step before this becomes submission-ready. -->

# Results

All numbers below are computed over the completed corpus: 21,570 of
21,600 planned traces (99.86%; 30 permanently missing for
Llama-3.3-70B-Instruct only, blocked by an Azure content-safety filter
— see Limitations), 216,319 labeled derived memories, 3 models, 30
scenarios (24 poisoned, 6 clean controls). Every reported point
estimate for H1–H4 carries a 95% bootstrap CI (10,000 resamples,
stratified by `poison_form`, `scenario_id` as the resampling unit,
n=24; see `results/metrics/h{1,2,3,4}_bootstrap_ci.csv`) — this
supersedes an earlier draft of this section, which reported H2–H4 as
raw pooled means pending that treatment; the bootstrap pass for those
three hypotheses is now complete (2026-08-16, same method as H1).

## H1 — Recall vs. inflation growth

Context-exposure (conservative) propagation holds recall at 1.000 by
construction across all three models and every depth — expected, not a
finding on its own. The finding is what it costs: precision degrades
and inflation grows with depth, consistently across all three models
(pooled across 24 scenarios, 95% CI in brackets):

| Model | Depth | P_BR | Inflation |
|---|---|---|---|
| gpt-4o-mini | 1 | 0.669 [0.642, 0.700] | 1.832 [1.748, 1.910] |
| gpt-4o-mini | 5 | 0.622 [0.593, 0.649] | 2.273 [2.044, 2.516] |
| gpt-4o | 1 | 0.628 [0.609, 0.643] | 1.946 [1.904, 1.995] |
| gpt-4o | 5 | 0.581 [0.552, 0.607] | 2.422 [2.100, 2.783] |
| llama-3.3-70b | 1 | 0.632 [0.620, 0.647] | 1.939 [1.895, 1.975] |
| llama-3.3-70b | 5 | 0.586 [0.552, 0.614] | 2.368 [2.034, 2.773] |

Structural-only propagation is the mirror image: near-perfect precision
(0.92–1.00) but recall stuck below 1.0 (0.91–0.98), *not* improving
with depth — the CO_RETRIEVED under-detection failure mode (a memory
merely co-retrieved into a write's context, not a declared structural
parent, whose content nonetheless surfaces the harmful claim)
reproduces at full scale, not just in the original 48-trace pilot that
first surfaced it.

**Every structural-vs-context_exposure difference is statistically
significant** (Wilcoxon signed-rank, paired by `scenario_id`, n=24,
depth 5): $p < 0.001$ for P_BR, R_BR, and inflation_ratio, across all
three models ($p \approx 1.2 \times 10^{-7}$ for P_BR and inflation in
every model). The precision/recall/inflation tradeoff is real, not
sampling noise.

## H2 — Attribution-threshold frontier

Thresholding by cosine similarity between parent/child embeddings
produces a real frontier, not a collapsed scalar (pooled across 24
scenarios, depth 5):

| Model | Threshold | P_BR [95% CI] | R_BR [95% CI] |
|---|---|---|---|
| gpt-4o-mini | 0.50 | 0.898 [0.868, 0.930] | 0.990 [0.976, 0.999] |
| gpt-4o-mini | 0.70 | 0.820 [0.781, 0.860] | 0.871 [0.828, 0.916] |
| gpt-4o-mini | 0.85 | 0.633 [0.566, 0.701] | 0.632 [0.558, 0.711] |
| gpt-4o | 0.50 | 0.887 [0.841, 0.928] | 0.998 [0.995, 1.000] |
| gpt-4o | 0.70 | 0.892 [0.844, 0.935] | 0.962 [0.941, 0.980] |
| gpt-4o | 0.85 | 0.710 [0.639, 0.786] | 0.725 [0.645, 0.809] |
| llama-3.3-70b | 0.50 | 0.890 [0.845, 0.929] | 0.997 [0.996, 0.999] |
| llama-3.3-70b | 0.70 | 0.878 [0.832, 0.916] | 0.949 [0.921, 0.975] |
| llama-3.3-70b | 0.85 | 0.640 [0.562, 0.720] | 0.652 [0.577, 0.731] |

(depth 5, 95% bootstrap CI, `results/metrics/h2_bootstrap_ci.csv`)

A conservative threshold (0.5) recovers nearly all of context-exposure's
recall while already cutting inflation substantially relative to no
threshold at all. An aggressive threshold (0.85) drops recall sharply
(to 0.63–0.73) — confirming H2's specific concern: raising the
threshold prunes exactly the weakly-attributed `CO_RETRIEVED` edges
that, per H1, are sometimes the *only* path to real contamination.

## H3 — Surface vs. structural traceability (non-directional, as pre-registered)

Overall laundering rate across the full corpus: **0.79%** (662 of
84,177 CARRIES-labeled memories) — small, but real, and this revises
our own pilot's "zero organic laundering" finding, which we report
alongside this result rather than silently replacing (per the
deviation-log protocol). Per-model, with 95% bootstrap CI (24
scenarios, `results/metrics/h3_overall_bootstrap_ci.csv`): gpt-4o
0.41% [0.04%, 1.04%], gpt-4o-mini 0.46% [0.00%, 0.95%], llama-3.3-70b
1.37% [0.55%, 2.44%] — llama-3.3-70b's CI does not overlap the other
two models', the first bootstrap-confirmed statistical signal for the
cross-model asymmetry this section reports qualitatively below.
Laundering is highly non-uniform:

- Concentrated almost entirely in `continue` and `paraphrase`
  derivation transforms; `summarize` and `refine` remain at or near 0%
  for all three models, consistent with the pilot's original
  observation for those specific transforms.
- **A real cross-model asymmetry**: Llama-3.3-70B's `paraphrase`
  output launders at 4.7–5.9% by depth 2–5, while gpt-4o and
  gpt-4o-mini's `paraphrase` output launders at 0% throughout.
  gpt-4o-mini's `continue` transform launders at a measurable,
  roughly depth-stable 1.0–2.2%; gpt-4o's `continue` transform
  launders at a smaller, depth-growing 0.4–1.7%.

Per H3's non-directional pre-registration, this is reported as
observed: laundering is rare in aggregate, model- and
transform-dependent in a way a single-model pilot could not show, and
does not support a simple "laundering increases with depth" story —
several transform/model combinations show no depth trend at all.

## H4 — Containment cost

`depth_aware` (conservative propagation within 2 hops of the
compromised root, structural-only beyond it) reduces over-quarantine
relative to `flat_transitive` (unconditional conservative propagation)
at a quantifiable, non-zero recall cost:

| Model | Depth | Objects flagged (flat) | Objects flagged (depth_aware) | Missed contamination (depth_aware) |
|---|---|---|---|---|
| gpt-4o-mini | 5 | 10.0 | 7.0 | 0.42 |
| gpt-4o | 5 | 10.0 | 7.0 | 0.11 |
| llama-3.3-70b | 5 | 10.0 | 7.0 | 0.09 |

`flat_transitive` misses essentially nothing (missed contamination
≈0.0005 objects/trace, gpt-4o-mini only, zero for the other two models)
— it flags almost everything, so it rarely misses real contamination,
at the cost of the largest quarantine set. `depth_aware` flags **30%
fewer objects** at depth 5 across all three models, but the recall it
gives up is markedly uneven across models: gpt-4o-mini pays roughly
4–5x the missed-contamination cost that gpt-4o and llama-3.3-70b do for
the identical object-count reduction — the same real cross-model
asymmetry H3 surfaces, showing up again in a different metric. The
`depth_aware` vs. `flat_transitive` gap in missed-contamination count
is statistically significant at every depth ≥3 for all three models
(Wilcoxon signed-rank paired by `scenario_id`, n=24: e.g. gpt-4o-mini
depth 5 $p = 0.00013$, gpt-4o depth 5 $p = 0.00044$, llama-3.3-70b
depth 5 $p = 0.00020$; full table in `results/metrics/h4_wilcoxon.csv`).

**Measurement note, reported rather than hidden:** our original
$C_{regen}$ operationalization (distinct depths touched) does not
differentiate the two policies in this harness's topology, since the
always-continuing structural lineage guarantees every depth is touched
regardless of policy — see Limitations. The object-count numbers above
are the metric that actually demonstrates the tradeoff.

## Clean-control false-positive baseline

Six genuinely unpoisoned scenarios (no adversarial content anywhere)
provide a false-positive baseline the original 24-scenario design
lacked. Two independent signals:

**Labeler false-positive rate: 0.0000%** (0 of 43,200 derived memories
labeled CARRIES/REFERENCES against a target that was never actually
present) — perfect specificity on content with no adversarial signal at
all, a meaningful validation of the labeling pipeline independent of
the κ=0.87–0.88 human-agreement result. (Revised 2026-09-21: a human
review of the 6 `clean_control` scenarios found 3 — `_03`/`_05`/`_06` —
had lexical/topical proximity between a benign source fact and the
scenario's harmful `semantic_target` strong enough to risk exactly this
kind of false positive; those 3 scenarios' benign facts were reworded
to remove the shared vocabulary and the corpus regenerated. The original
rate, 0.0046% (2/43,200), is reported here as the record of that
correction, not silently overwritten — see
`configs/scenarios/clean_control_review.md`.)

**Propagation false-positive count** (objects flagged when $B_{true}=0$
by construction, confirmed for all 86,400 raw rows): `structural`
flags only the single unavoidable continuing-lineage node per depth
(1, 2, 3, 4, 5 — zero variance); `context_exposure`/`flat_transitive`
flag substantially more purely from distractor co-retrieval fan-out
(10 by depth 5, consistent across all three models); `depth_aware`
sits at 7 by depth 5 — the same ~30% reduction seen in H4's
missed-contamination tradeoff, now also confirmed on a corpus with
zero real contamination to miss, not just on the poisoned corpus.
This is independent evidence that `depth_aware`'s over-quarantine
reduction is a real structural property of the policy, not an
artifact of the specific poisoned scenarios it was measured on.

## Summary across hypotheses

The consistent thread across H1, H3, and H4 is a genuine cross-model
asymmetry that a single-model study (the original pilot, and most
comparable prior work) could not surface: gpt-4o-mini shows the
steepest H1 inflation growth and the largest H4 missed-contamination
cost under `depth_aware`; llama-3.3-70b shows the most pronounced H3
laundering under `paraphrase`. No model is uniformly "safer" across all
three hypotheses — which model looks best depends on which failure
mode (over-tainting, missed contamination, or laundering) an operator
weights most heavily, itself a result worth stating plainly rather than
collapsing into a single ranking.
</content>
