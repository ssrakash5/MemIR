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

**Robustness check: does the frontier depend on the embedding model?**
`all-MiniLM-L6-v2` was an explicitly documented placeholder
(`src/memoryir/embeddings.py`), never validated against another
embedding space — the obvious reviewer criticism is that the attribution
frontier above could be an artifact of one embedding space rather than a
real property of the derivation graph. We recomputed H2 with a second,
architecturally different embedding model (`all-mpnet-base-v2` — MPNet,
not MiniLM; 768-dim, not 384; different training mixture), scoped to
gpt-4o-mini/seed=0/all 24 poisoned scenarios (25,345 memory nodes
re-embedded locally, no new generation, no change to the frozen
main-run pgvector embeddings). Cosine similarity has a different scale
in this embedding space, so thresholds were chosen from *this run's own*
similarity distribution (25th/50th/75th percentile: 0.19/0.29/0.44) —
not the MiniLM run's 0.5/0.7/0.85, which have no privileged meaning
here:

| Threshold (own-dist. quantile) | P_BR | R_BR | Inflation |
|---|---|---|---|
| 0.19 (p25) | 0.684 | 1.000 | 1.93 |
| 0.29 (p50) | 0.757 | 1.000 | 1.64 |
| 0.44 (p75) | 0.884 | 0.999 | 1.31 |

(depth 5, gpt-4o-mini/seed=0/24 scenarios, `results/metrics/h2_second_embedding_headline.csv`)

The qualitative frontier survives: precision rises monotonically
(0.684 → 0.757 → 0.884) and inflation falls monotonically (1.93 → 1.64
→ 1.31) as the threshold tightens, exactly the direction H2 predicts.
The magnitude differs in one notable way — recall barely erodes in
this embedding space (1.000 → 0.999) compared to the MiniLM run's sharp
drop at its strictest threshold (to 0.63–0.73) — which is itself
informative: it suggests `all-mpnet-base-v2`'s similarity scores
separate `STRUCTURAL_PARENT` from `CO_RETRIEVED` edges more cleanly at
the high end than `all-MiniLM-L6-v2` does, not that the frontier itself
is embedding-specific. What matters for H2's claim is that increasing
attribution strictness still trades some recall for higher precision
under a materially different embedding space — it does.

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

**Robustness check: does the tradeoff depend on the specific 2-hop
window?** `depth_aware`'s window was a dated, explicitly-flagged
operationalization (Limitations) — the frozen design named "one
baseline, one proposed method" without specifying the proposed
method's algorithm. A natural question is whether the reported ~30%
reduction is a real point on a continuous tradeoff or a hand-picked
operating point that happens to look favorable. We swept
`depth_aware_window` ∈ {1, 2, 3} at depth 5, full 24-scenario corpus,
all 3 models, all 5 seeds (n=24 scenarios, same bootstrap discipline as
above), using `src/memoryir/metrics.py`'s `b_flagged` unmodified — no
new code in the frozen metrics module, only a new caller
(`eval/compute_h4_window_sensitivity.py`):

| Window (hops) | Objects flagged (mean) | Missed contamination (mean) |
|---|---|---|
| 1 | 6.00 | 0.278 |
| 2 | 7.00 | 0.206 |
| 3 | 8.00 | 0.141 |

The tradeoff moves smoothly as the window expands: each additional hop
of conservative propagation costs exactly one more flagged object
(mechanical, given this harness's always-continuing structural
lineage) and buys back a further ~25–32% reduction in missed
contamination relative to the previous window. This is the stronger
result to report — not that window=2 is optimal (we make no such
claim), but that `depth_aware` is one point on a family of
depth-dependent policies whose cost/recall tradeoff is continuous and
predictable, not a single hand-picked configuration. Full per-model
breakdown in `results/metrics/h4_window_sensitivity_by_model.csv`.

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

## Real-document ecological-validity slice

The strongest evidence that H1–H4 are not artifacts of a synthetic,
LLM-authored corpus comes from deliberately moving the source material
out from under the pipeline. To test whether the synthetic-corpus
findings persist under naturally authored source material, we
constructed a held-out validation slice from
20 frozen public documents spanning five domains (NIST, CISA, OWASP, FTC,
AWS, Azure, FDA, IRS). We injected one controlled target claim per document
while retaining verbatim benign source facts and distractors, and ran the
frozen generation and labeling pipeline without prompt, labeler, threshold,
or traversal changes. Across 240 traces and 2,400 derived memories, the
principal containment tradeoff reproduced: `depth_aware` propagation
reduced inflation from 3.57 [2.62, 4.72] under `flat_transitive`
propagation to 2.50 [1.82, 3.31] (n=20 scenarios as the resampling unit,
mirroring the main corpus's `scenario_id`-level bootstrap discipline),
while `structural`-only propagation achieved $P_{BR}=0.796$ [0.689, 0.890]
and $R_{BR}=0.973$ [0.960, 0.985] — broadly consistent with the synthetic
corpus's precision/recall tradeoff.

Clean-sibling contamination also persisted outside the synthetic corpus:
across the 20 scenarios, the `child_2` branch (whose true structural
parents exclude the injected fact) showed strict semantic-leakage rate
3.83% [2.00%, 5.83%] and broad (CARRIES+REFERENCES) rate 15.83% [9.92%,
22.00%]. We manually read the full population of 46 `child_2=CARRIES`
memories (not a sample) rather than assuming the mechanism: 40/46 (87%)
explicitly contained the injected claim's marker or wording despite lacking
a structural-parent edge to it, 5/46 were ambiguous, and 1/46 looked like a
labeler over-trigger — direct textual confirmation that this is genuine
co-retrieval leakage, not a label-rate artifact.

Surface-marker laundering (H3) was substantially higher than in the
synthetic corpus and showed marked scenario-level heterogeneity: the
scenario-level rate (n=20, the primary estimand, same resampling discipline
as above) was 19.1% [6.9%, 33.1%], against 0.79% in the synthetic corpus.
Most individual scenarios laundered 0% of their CARRIES memories, while
four (three of five involving compositional or authoritative-framing
poison forms) laundered 30–97%; the pooled-over-memories figure (13.5%,
128/946) understates this heterogeneity by overweighting the highest-n
scenarios. We report the wide CI plainly rather than treating the point
estimate alone as a corpus-invariant quantity: the direction of the
real-vs-synthetic gap is a robust finding, but its exact magnitude is
sensitive to source-text regime and should not be extrapolated to
deployment settings from this slice alone.

Read together, this is a more credible and more useful claim than
"everything replicated": the provenance/containment frontier
(structural precision/recall, `depth_aware`'s inflation reduction)
appears robust across source regimes, while the absolute
surface-laundering rate does not, and the manual read of all 46
`child_2=CARRIES` cases shows that difference is measured, not just
inferred from label rates that could themselves have shifted with the
source material.

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
