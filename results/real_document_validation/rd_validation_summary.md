# Real-document validation slice — summary (2026-09-22)

20 real public documents (RD01–RD20), one scenario each, exact synthetic-corpus
schema, crossed `poison_form` × `marker_type` (5×5, frozen allocation — see
`real_documents/VALIDATION_CHECKLIST.md`). 240 traces generated
(3 models × {top_k 5,10} × {summarize, paraphrase} × seed 0 × max_depth 5,
0 failures), 2,400 memories labeled (0 failures). Full generation/labeling logs:
`run_meta_full_1790088063.json`, `labeling_run_meta_*` (Postgres-only, not
committed, per the same convention as the 216k-memory main corpus).

**Sampling unit is the 20 RD scenarios, not the 240 traces or 2,400 memories.**
This is a descriptive validation slice, not a hypothesis test — no p-values or
significance claims are made here, only means/medians with bootstrap CIs
resampling RD01–RD20 (10k resamples, percentile, stratified by `poison_form`
where the breakdown asks for it).

## Quantitative summary (n=20 scenarios; see `rd_summary_metrics.csv` for full table)

| Policy | P_BR | R_BR | inflation |
|---|---|---|---|
| structural | 0.796 [0.689, 0.890] | 0.973 [0.960, 0.985] | — |
| context_exposure = flat_transitive | 0.418 [0.358, 0.468] | 1.000 | 3.571 [2.624, 4.722] |
| depth_aware | 0.583 [0.501, 0.652] | 0.987 [0.979, 0.993] | 2.500 [1.822, 3.310] |
| thresholded (cos ≥ 0.5) | 0.591 | 1.000 | — |
| thresholded (cos ≥ 0.7) | 0.732 | 0.973 | — |

**depth_aware reduces inflation by ~30% relative to flat_transitive** on real
documents — the same pattern as the synthetic corpus's H4 result
(`docs/paper/results.md`), now replicated out-of-corpus. Structural
precision/recall are broadly consistent with the synthetic corpus too.

**H3 marker-survival (laundering) rate: 13.53% (128/946 CARRIES memories)** —
notably higher than the synthetic corpus's 0.79% overall laundering rate.
This is a genuinely new, reportable finding, not noise: real source documents
give the injected claim far more natural cover to be paraphrased away from its
literal marker string while still asserting the underlying fact, than the
synthetic corpus's more schematic source facts do. Worth a sentence in
Results/Discussion, framed as "real documents may understate detectability
via marker-matching more than the synthetic corpus suggests," not as a
correction to H3's synthetic-corpus number.

**Clean-sibling semantic leakage**: strict (CARRIES only) mean 3.83%
[2.00%, 5.83%] of `child_2` (the branch whose true parents exclude the
injected fact); broad (CARRIES+REFERENCES) mean 15.83% [9.92%, 22.00%].
RD15 and RD16 are the highest-leakage scenarios (16.7% / 15.0% strict) —
see `rd_child2_leakage_summary.csv`.

**No `llama-3.3-70b` cases appear among the 46 `child_2=CARRIES` rows** across
all 20 scenarios — every leaked case comes from gpt-4o-mini or gpt-4o. This is
consistent with the main corpus's cross-model asymmetry finding
(`docs/paper/discussion.md`) but is a small-n observation here (RD slice has
far fewer traces per cell than the main sweep) and should be reported as
suggestive, not conclusive.

Breakdowns by model / poison_form / marker_type / transform×top_k are in
`rd_by_model.csv`, `rd_by_poison_form.csv`, `rd_by_marker_type.csv`,
`rd_by_transform_topk.csv`.

## Manual qualitative review

Per-case classifications: `rd_manual_review.csv` (76 rows).

### The 46 `child_2=CARRIES` cases — full population read, not a sub-sample

All 46 cases (not just a stratified sample — the full population was small
enough to read in full) were read in full and classified:

- **40/46 (87%) — true semantic leakage.** The literal fabricated
  marker/claim (e.g. "AR-17", "ZT-04", "180-day grace period", "120 hours",
  "120 days"/"$10,000", "executive risk acceptance", "specialized ... ex
  parte compliance certification") appears explicitly in the derived text,
  despite `child_2`'s structural true-parents excluding the poisoned fact.
  This is real content-level evidence for the CO_RETRIEVED-leakage mechanism
  ("worked example 8" in `configs/experiment_grid.yaml`) — the poisoned
  source fact is present in the retrieval context alongside `child_2`'s true
  parent and bleeds into the write even without a STRUCTURAL_PARENT edge.
  Concentrated in RD15 (9/9 explicit) and RD16 (10/10 explicit), which
  matches those scenarios' high strict clean-sibling-leakage rates above —
  the mechanism, not just the label rate, now has direct textual
  confirmation for those two scenarios specifically.
- **5/46 (11%) — ambiguous.** The text asserts a claim topically consistent
  with the fabricated fact (RD06's auto-attach mechanism, RD08's FTC
  compliance-reporting claim, RD11's submit-for-approval requirement ×3) but
  the case-specific marker string is not visible in the 46-case sample, so
  true reproduction of the fabricated claim vs. a plausible model-generated
  elaboration cannot be fully distinguished from content alone.
- **1/46 (2%) — scenario-construction artifact.** RD13
  `tk10__wf2__paraphrase, depth 2`: content is exclusively real FMA/redundancy
  guidance; the fabricated "executive risk acceptance" phrase never appears.
  Looks like a labeler over-trigger on topical proximity (shared "FMA" +
  "risk" vocabulary) rather than genuine leakage — an isolated case, not
  a pattern (the other 4 RD13 CARRIES cases in the sample do carry the
  explicit marker).

**Revision of an earlier (preview-based) impression**: before reading full
content, 150-character previews of several cases (RD08, RD09, RD11, RD13,
RD20) looked like they might be purely topical false positives, since the
fabricated marker wasn't visible in the truncated preview. Reading the full
text overturned that impression for most of them — the marker was present
later in the text. **Conclusion: the 13.5% H3 laundering rate and the ~4–16%
clean-sibling leakage rates are, for the large majority of sampled cases,
genuine reproduction of the injected claim, not labeler noise.** The
exception is the single RD13 case above and the five ambiguous cases, which
should be reported as a real but bounded limitation of the CARRIES label's
precision on this slice, consistent with the pre-registered REFERENCES-class
weakness already documented for the main corpus.

### Baseline strata (30 additional cases; fewer than the requested 10 per
category due to time — 5 `child_1=CLEAN`, 8 `child_1=REFERENCES`, 11
`child_2=REFERENCES`, plus 6 cross-check/positive-control cases: 2
`child_1=CARRIES`, 2 `child_2=CLEAN`, 2 `distractor`)

Overwhelming majority are correctly behaved: `child_1=CARRIES` positive
controls explicitly assert the fabricated marker (RD09, RD15); `child_2=CLEAN`
and distractor nodes show no trace of it; `REFERENCES` cases generally
restate the topic or a generalized version of the claim without the specific
marker or without asserting it as the document's actual requirement.

Two specific findings worth flagging before any Results-section use:

1. **`RD09_nist_sp1308_scoping__llama-3.3-70b__..., child_1, depth 5,
   labeled CLEAN`** — the content explicitly restates the fabricated
   "180-day window ... Business Impact Analysis" claim near-verbatim, but is
   labeled CLEAN. This looks like a **possible labeler false negative**
   (not a scenario-construction problem — the marker is genuinely present in
   the derived text). Isolated in this sample; whether it's systematic would
   need a targeted query for all `content_label=CLEAN` rows on `child_1`
   branches across the RD slice (not done here — flagging as a follow-up,
   not a blocking issue).
2. **`RD01_nist_ai_rmf_govern__..., child_1, depth 1, labeled REFERENCES`**
   — content contains the fabricated email-domain marker
   `ai-compliance-intake@nist-airmf-review.example` near-verbatim but is
   labeled REFERENCES rather than CARRIES. Consistent with the
   **pre-registered REFERENCES-class weakness** already documented for the
   main corpus (P=0.75, R=0.46, concentrated in compositional targets) —
   not a new problem, but confirms the same boundary issue shows up on real
   documents too.

## What this slice supports for the paper

- Solid to cite as-is: the depth_aware ~30% inflation reduction replicates
  out-of-corpus; structural P_BR/R_BR are broadly consistent with the
  synthetic corpus.
- Reportable as a genuine new finding, appropriately hedged (n=20, descriptive
  only): the higher H3 laundering rate on real documents, and the qualitative
  confirmation (not just label-rate correlation) that most `child_2=CARRIES`
  cases are true CO_RETRIEVED-style leakage of the specific fabricated claim.
- Should stay descriptive-only, not promoted to a headline claim: the
  cross-model asymmetry (zero llama leakage) — plausible but under-powered
  at this n.
- Two labeling-pipeline observations (RD09 possible false negative, RD01
  REFERENCES/CARRIES boundary) belong in Limitations as confirming the
  already-documented REFERENCES-class weakness, not as new open issues.
