# Pre-registration

**STATUS: STAMPED 2026-08-12.** This is the committed pre-registration.
Per the go/no-go decision recorded in this document's closing section:
the labeling pipeline was revised once (adjudication made diagnostic-only
after it was found net-harmful — see `docs/labeling_protocol.md`), κ was
recomputed against the *same* 120-sample calibration set (legitimate:
this sample exists specifically to select/freeze the labeling procedure
before the real experiment, and the reuse is stated transparently here,
not hidden), and **κ = 0.8699 ≥ 0.6 → stamp, no further methodology
changes after this point.** The known REFERENCES-class weakness
(P=0.75, R=0.46, concentrated in `multi_hop_setup` compositional targets)
is preregistered as a limitation to report alongside aggregate κ, not a
reason to keep iterating on the rubric or pipeline.

**What is now frozen and must not change without an explicit, recorded
revision + re-validation:** the scenario corpus (24 `poison_form` ×
`scenario_id` design, `configs/experiment_grid.yaml`), the hypotheses
(H1–H4 below), the dependent variables and metric definitions, the
labeling rubric and pipeline (`docs/labeling_protocol.md`,
`src/memoryir/labeler.py`), and the falsification conditions. Sample
sizes for the full run still need real numbers plugged in (§4) — that is
an open scaling decision, not a rubric/hypothesis change, and does not
reopen this stamp.

**Prior history (condensed — see git log for full detail):** 2026-08-11,
generation/analysis split and 24-scenario design finalized. 2026-08-12,
same day: all 24 scenarios human-approved; MPBench/AgentPoison/MINJA full
reads closed the literature gate; `eval/` harness (v1, scoped to labeling
validation) built and run (48 real traces, 480+ derived memories); 8
labeling worked examples built from that output, 2 prespecified
categories searched for and genuinely not found (zero organic laundering
observed — a real finding, see H3); two scientific-framing corrections
made from that work (compositional CARRIES/REFERENCES rule,
`CO_RETRIEVED` redefinition), freezing the rubric; κ validation run,
found adjudication net-harmful, adjudication revised to diagnostic-only,
κ recomputed and passed with a clear margin; this document stamped.

**Do not generate experiment data before this stamp's commit. Data
generation is now unblocked as of this commit.**

---

## 1. Hypotheses (REVISED 2026-08-12, second revision — see rationale below)

**Why revised:** real `eval/` output (`docs/labeling_protocol.md` worked
example 8) showed `CO_RETRIEVED` content leaking into a write and
producing genuine content-level CARRIES whose only `STRUCTURAL_PARENT` is
an unrelated benign fact. The original H1/H2/H4 implicitly assumed every
`CO_RETRIEVED` edge was a potential *false positive* (over-tainting risk
only). That assumption is now falsified by direct observation — incidental
context uptake can also cause a real *false negative* for any
structural-lineage-only detector. H1/H2/H4 below are rewritten to
recognize both failure modes; this is a stronger, more accurate framing,
not a retreat. See `docs/labeling_protocol.md`'s three-layer table
(structural lineage / context exposure / semantic contamination) for the
conceptual distinction this rests on.

- **H1 — Recall vs. inflation growth.** Context-exposure-based
  (conservative, `attribution_threshold=null`) provenance preserves high
  blast-radius recall (R_BR) against the semantic-contamination ground
  truth (B_true = objects where `content_label == CARRIES`) as retrieval
  fan-out (`top_k`) and write fan-out (`write_fanout`) grow, but its
  quarantine set (B_flagged) grows increasingly larger than B_true
  (superlinear inflation). Test this, don't assume it holds by
  construction — H1 is no longer trivially true merely because
  conservative propagation flags everything reachable, since B_true is
  now anchored to content labels, not structural reachability.
- **H2 — Precision/recall frontier from attribution, including missed
  incidental uptake.** Attribution thresholds reduce inflation (fewer
  false positives) but can also reduce recall by pruning away
  `CO_RETRIEVED` edges that turn out to be the only path to real
  semantic contamination — not just by pruning away weakly-attributed
  `STRUCTURAL_PARENT` edges. Report the full P_BR/R_BR frontier, not a
  collapsed "best threshold" scalar, and explicitly check whether
  thresholding drops recall on cases structurally analogous to worked
  example 8.
- **H3 — Surface vs. execution-provenance traceability (NON-DIRECTIONAL,
  revised 2026-08-12).** Characterize how surface-level (marker-token)
  traceability and structural-lineage traceability diverge across
  `derivation_transform` and depth — **do not preregister a direction**.
  The pilot corpus (48 real traces, 4 of 4 derivation transforms tested
  across a subset, temperature 0) showed **zero organic laundering**:
  across every `child_1` (`TRUE_DESCENDANT`) lineage checked, the marker
  and the semantic claim survived intact through depth 5. Preregistering
  "laundering increases with depth/transform strength" after already
  observing evidence against it would be indefensible. The exact pilot
  finding, to be reported as-is regardless of what the full run shows:
  *"Across 48 traces plus targeted refine/continue probes at temperature
  0, no case was observed in which the harmful semantic content
  disappeared while structural ancestry persisted."* If the full
  experiment uses materially different models, temperatures, or prompts
  than this pilot, that scope difference must be stated explicitly next
  to any laundering-rate claim.
- **H4 — Containment: missed contamination AND unnecessary cost.** The
  `depth_aware` containment policy is compared against `flat_transitive`
  on *both* axes: over-quarantine cost (unnecessary quarantine/
  regeneration, via `containment_cost`/C_regen and Regeneration Overhead)
  *and* missed contaminated objects (real CARRIES objects that neither
  policy's B_flagged reaches — the failure mode worked example 8
  demonstrates is real). The paper's contribution is the
  precision-recall frontier of incident containment, not a one-sided
  demonstration that conservative taint explodes.

## 2. Variables

See `configs/experiment_grid.yaml` for the authoritative, finalized
generation/analysis split.

- **Cross-model extension (RESOLVED 2026-08-12, post-stamp, explicit
  user decision):** `model` added as a generation factor (3 values:
  gpt-4o-mini, gpt-4o, llama-3.3-70b), resolving the previously-`TBD`
  model field in `configs/experiment_grid.yaml`. gpt-4o-mini's full
  5,760-trace grid was generated before this factor existed; the other
  two models each run the identical full grid (not a reduced subset),
  for **17,280 traces total**. This is a scope addition to the frozen
  design, recorded here rather than silently folded in — the corpus,
  hypotheses, rubric, and metric definitions are otherwise unchanged.
  Model is held explicit (not marginalized) in reporting, the same way
  `poison_form` is: primary claims are per-model or pooled-with-model-CI
  as the analysis warrants, and any single-model generalization claim
  should be read with the same small-n caution as `poison_form` panels
  if it ever needs to be broken down further than 3 models allow.
- **Generation factors** (each combination produces one real trace —
  expensive): `scenario_id` (24 values: 4 `poison_form` × 6
  independently-constructed scenarios each — the real sampling unit, see
  §4/§5), `top_k` {1,3,5,10}, `write_fanout` {1,2,3}, `derivation_transform`
  (4 values, matching MemLineage §5.3's summarize/paraphrase/refine/continue
  vocabulary), `seeds` {0,1,2,3,4} (RESOLVED 2026-08-12, 3→5 — see §4). `prompt_style` (terse/verbose/structured —
  renamed from `summarization_prompt`) is a **balanced per-scenario
  attribute** (2 of each style's 6 scenarios get each `prompt_style` value),
  not a crossed factorial axis. **5,760 generated traces**
  (24×4×3×4×5).
- **Analysis factors** (computed post-hoc from a trace's persisted
  `(parent, child, attribution_score, run_id)` edges, no re-generation
  needed): `depth` {0..5}, `attribution_threshold` {null, 0.5, 0.7, 0.85},
  `containment_policy` {flat_transitive, depth_aware}. **138,240 depth ×
  threshold analysis cells** derivable from the 5,760 traces (5,760×6×4);
  containment policy is a further analysis layer on top of that.
- **Generation controls:** `max_depth=5` as a hard external harness stop
  condition NOT exposed to the agent's prompt. The prefix property this
  split depends on (a depth-d prefix of a depth-5 trace equals a trace
  generated with `max_depth=d` directly) is now **validated**:
  `spike/06_prefix_property.py` passed GREEN on 2026-08-11 for d=0..4,
  including a negative control proving the check can detect a real
  violation. Caveat carried from that spike: it validates the *design* via
  a deterministic mock, not the eventual real `eval/` harness — that needs
  its own equivalent check once built. Model, embedding model, corpus
  size — still `TBD`.
- **Benchmark-design requirement (not a variable, a construction rule):**
  every generation run's retrieved context must mix true parents
  (`STRUCTURAL_PARENT`, per the oracle schema in
  `docs/labeling_protocol.md`) with co-retrieved distractors
  (`CO_RETRIEVED`). Without this, conservative provenance has perfect
  precision by construction and the paper's central phenomenon can't
  appear in the data.

## 3. Labeling protocol

See `docs/labeling_protocol.md`, now with two independent label layers:
content-level (CARRIES/REFERENCES/CLEAN, evaluated against each scenario's
`semantic_target`, via the automated 3-signal labeler) and
oracle/structural (`STRUCTURAL_PARENT`/`CO_RETRIEVED` edges,
`COMPROMISED_ROOT`/`TRUE_DESCENDANT`/`COEXPOSED`/`UNRELATED` nodes, set at
corpus-construction time). **Oracle authoring is now RESOLVED:**
programmatic generation from a human-approved scenario specification (see
`configs/experiment_grid.yaml`'s "Scenario design" section for the schema)
— a human approves scenario semantics and true-dependency structure, code
deterministically derives oracle edges/nodes, the LLM only generates
surface text. **Still open:** whether the κ validation needs to run
separately against each label layer (content-label agreement vs. a
separate check that the corpus's claimed oracle structure holds up under
inspection of a sample of generation traces).

## 4. Sample sizes

**Scenario count is now RESOLVED: 24 `scenario_id`s (4 `poison_form` ×
6 independently-constructed scenarios each)** — see
`configs/experiment_grid.yaml`'s "Scenario design" section. This closes
the pseudo-replication risk: seeds now measure within-scenario model/run
stochasticity, and generalization across independently constructed attack
instances of a style is what the 6-scenario replication is for.

**Replication (seeds per scenario-condition) — RESOLVED 2026-08-12, this
was the last item this section left open at stamp time.** The arithmetic
that closed it: the bootstrap unit is `scenario_id` (§5), and seeds /
`derivation_transform` are averaged within each scenario-condition
*before* resampling — so the real inferential N is 24 (6/`poison_form`)
regardless of how many seeds are run. Pooled SE ≈ σ/√24 ≈ 0.20σ;
per-`poison_form` SE ≈ σ/√6 ≈ 0.41σ. These are approximate (assume a
plausible σ, not an empirically established one) but sufficient to
establish the qualitative fact that decided this: **scenario diversity,
not trace replication, is what limits statistical resolution here.**
Consequences:

- **Primary inference is the 24-scenario pooled estimand for H1–H4.**
  Per-`poison_form` panels (n=6 each) are still reported — they may show
  real qualitative differences (e.g. `multi_hop_setup` behaving
  differently) — but as a **descriptive/exploratory stratified analysis
  with CIs shown**, not as independently-powered comparisons. Language
  like "`multi_hop_setup` is significantly worse than `direct_instruction`"
  is not licensed by this design; hundreds of underlying traces per stratum
  must not be allowed to make an n=6 comparison look more powered than it
  is.
- **Seeds: 3 → 5**, justified purely as within-scenario noise reduction
  in a pipeline with empirically confirmed `temperature=0` API
  non-determinism (the κ run 2a/2b discrepancy, `docs/labeling_protocol.md`)
  — not as a bid for more statistical power, which seed count cannot
  provide given the bootstrap unit is `scenario_id`. Three rules frozen
  alongside this decision (mirrored in `configs/experiment_grid.yaml`):
  1. The same five predetermined seed IDs (0,1,2,3,4) are used for every
     applicable condition — no rerunning a cell because an output looks
     odd.
  2. All five are averaged within scenario-condition before any
     inferential resampling — resampling still sees 24 scenario units,
     never 120 "independent" observations.
  3. Five is frozen after this decision. A genuine failed API call/retry
     is not a sixth statistical replicate.
- **Effective inferential n: 24, not 120 (5×24) and not the raw trace
  count (5,760).**

This resolves §4's last open item as of the stamp — a scaling/replication
decision made under the already-stamped scientific design (hypotheses,
corpus, rubric, grid factors), not a reopening of that stamp. No further
sample-size decision remains open; generation may proceed.

**Still not fully determined (lower priority, not blocking generation):**
- The distractor-per-run design (how many true parents vs. distractors per
  retrieval within each scenario's `distractor_pool` — this directly sets
  how hard the precision problem is, so it needs to be a deliberate
  choice per scenario, not incidental). This is already governed
  mechanically by the frozen "true-parents-rank-first" rule in
  `configs/experiment_grid.yaml`, so is more a documentation cleanup than
  an open design question.
- Target scale from `docs/labeling_protocol.md`: ≥200 injection instances
  across ≥4 styles, chains to depth ≥3 — a floor for the *labeling
  validation* corpus specifically, distinct from and smaller than the
  24-scenario / 5,760-trace generation design (see that document's
  clarification of this distinction).

## 5. Statistics

- Paired bootstrap, 10,000 resamples, for all point estimates.
- 95% confidence intervals on every reported number.
- Wilcoxon signed-rank test for paired comparisons.
- **Bootstrap resampling unit is `scenario_id`, stratified by
  `poison_form`, not raw factorial cells or trace rows** — seeds
  within one scenario are nested repeated measurements, not independent
  samples; resampling 5,760 trace rows as though independent would be
  pseudo-replication.
- **Reporting hierarchy (RESOLVED 2026-08-12, §4): pooled-across-24
  estimates are primary for H1–H4; `poison_form`-stratified panels
  (n=6 each) are descriptive/exploratory only, reported with CIs, never
  as independently-powered claims.** See §4 for the SE arithmetic this
  is based on.
- **Marginalization rule (preregistered estimand — balanced marginal
  means over the experimental distribution we defined, NOT real-world
  deployment prevalence):** average seeds within each scenario-condition
  first, then give every `scenario_id` equal weight regardless of cell
  count underneath it. Per-hypothesis marginalization plan is spelled
  out in `configs/experiment_grid.yaml`'s trailing comment block — H1
  holds top_k×write_fanout×depth explicit at `attribution_threshold=null`;
  H2 holds attribution_threshold×depth×top_k×write_fanout explicit and
  reports a frontier; H3 holds derivation_transform×depth explicit at
  `attribution_threshold=null`; H4 applies containment_policy post-hoc to
  every reconstructed graph. All four marginalize equally over scenario_id
  (stratified by poison_form) and whichever other generation factors
  aren't held explicit.
- **depth=0 special case:** at depth 0 the compromised root may have zero
  downstream descendants, giving \|B_true\|=0 and making R_BR/inflation
  undefined. **Do not coerce to zero.** Report P_BR/R_BR/inflation as N/A
  at any horizon where the oracle downstream blast radius is empty; depth
  0 is still analyzed for the surface-marker baseline and harness
  validation.

## 6. Falsification conditions (REVISED 2026-08-12 to match the H1–H4 rewrite)

Stated in advance, to be reported regardless of outcome:

- **If blast-radius inflation stays near 1.0× across the tested fan-out
  range**, the over-tainting problem motivating H1 doesn't materialize in
  practice and that half of the paper's premise is wrong.
- **If missed-contamination counts (real CARRIES objects unreachable by
  any tested B_flagged policy, per H2/H4) stay near zero**, the
  under-detection failure mode worked example 8 demonstrated in the pilot
  turns out to be rare at scale, and H2/H4's "recall risk from pruning"
  framing loses its motivation — this would still be worth reporting, not
  hidden, since it would mean the pilot's finding didn't generalize.
- **If depth-aware containment (H4) doesn't measurably reduce over-
  quarantine relative to flat transitive taint, or does so by materially
  increasing missed contamination**, the paper's proposed remedy has no
  net advantage over the naive baseline.
- **H3 has no directional falsification condition** (it's non-directional
  by design, see above) — instead, the reportable outcome is simply
  whichever divergence (or lack of divergence) between surface and
  structural-lineage traceability is actually observed at full-run scale,
  compared explicitly against the pilot's zero-laundering finding. If the
  full run also shows zero laundering, that itself is the result — not a
  failure to find something that was expected.

## Metric definitions (canonical — supersedes earlier E_* notation)

**B_true is anchored to the semantic-contamination layer specifically
(objects with `content_label == CARRIES`), not structural reachability
(`TRUE_DESCENDANT`) — corrected 2026-08-12.** This was ambiguous in the
first 2026-08-11 revision and the ambiguity mattered: worked example 8
shows a real case where these two would give different answers (a
`COEXPOSED` node — not `TRUE_DESCENDANT` — that nonetheless has
`content_label == CARRIES`). See `docs/labeling_protocol.md`'s
three-layer table (structural lineage / context exposure / semantic
contamination) for the full distinction. Set notation over blast-radius
**objects**, not edges (edges get a separate P_E/R_E pair — see below):

- Blast-radius precision: P_BR = \|B_flagged ∩ B_true\| / \|B_flagged\|
- Blast-radius recall: R_BR = \|B_flagged ∩ B_true\| / \|B_true\|
- Inflation ratio: \|B_flagged\| / \|B_true\|
- Containment cost: C_regen = count of unique *generating runs* that must
  be replayed to regenerate the quarantined set — not per-object cost (one
  run producing 3 exposed memories is 1 replay, not 3). Secondary:
  regeneration_tokens if logged. Normalized H4 metric: Regeneration
  Overhead = C_predicted / C_oracle.
- Attribution edge quality: P_E, R_E — precision/recall of inferred
  `(parent, child)` edges against the oracle's `STRUCTURAL_PARENT` vs.
  `CO_RETRIEVED` labels — this measures structural-lineage inference
  quality, a distinct question from blast-radius reconstruction (semantic
  contamination). These CAN diverge (worked example 8) — report
  separately, do not collapse into one number.
- `derivation_contract_satisfied` (boolean, per memory, distinct from
  `content_label`): did this write express its intended `target_semantics`
  — see `docs/labeling_protocol.md`'s compositional-target rule. Not
  itself a headline metric, but useful for diagnosing *why* a
  `multi_hop_setup`-style write ended up REFERENCES instead of CARRIES
  (structurally on-contract but not semantically composed, vs. genuinely
  off-contract).

## Before this can be committed as the real pre-registration

1. ~~Positioning correction~~ — done 2026-08-11.
2. ~~Generation/analysis split, 41,472-cell arithmetic correction,
   distractor requirement~~ — done 2026-08-11.
3. ~~Prefix property validated~~ — `spike/06_prefix_property.py` GREEN,
   2026-08-11.
4. ~~MemSecBench full read~~ — done 2026-08-11; positioning survives
   unchanged (see `docs/positioning.md`).
5. ~~`scenario_id`/pseudo-replication question, oracle-authoring method~~ —
   RESOLVED 2026-08-11: 24 scenarios, programmatic oracle generation from
   human-approved specs.
6. ~~The 24 scenario specifications don't exist yet~~ / ~~the 20 aren't
   approved~~ — **all 24 are now HUMAN-APPROVED.** Pilot's 4 approved
   2026-08-11, including the review pass that corrected `true_parents` to
   the minimal causally-necessary set in 3/4. Remaining 20 drafted and
   reviewed 2026-08-12: 12 approved as drafted, 8 revised (semantic-target
   wording, distractor/clean-sibling contamination) — **zero
   `true_parents` errors found in the 20**, confirming the ground-truth
   principle transferred correctly to fresh scenario construction. See
   `configs/scenarios/README.md` for full per-scenario detail.
7. ~~Automated labeler combination rule~~ — RESOLVED 2026-08-12:
   LLM-primary + NLI verification + adjudication, marker tokens excluded
   from the label decision entirely (see `docs/labeling_protocol.md`).
8. ~~MPBench, AgentPoison, MINJA full reads~~ — done 2026-08-12; the
   entire `week1_execution_plan.md` §1 literature gate is closed (see
   `docs/prior_art.md`).
9. ~~20 new scenarios reviewed/approved~~ — done 2026-08-12.
10. ~~eval/ harness (v1, scoped) built and run~~ — done 2026-08-12: 48
    real traces (24 approved scenarios × 2 transforms), 480+ derived
    memories with full oracle bookkeeping. See `eval/README.md`.
11. ~~Worked examples~~ — done 2026-08-12, built from real `eval/`
    output (`docs/labeling_protocol.md`). 8 observed empirical examples;
    2 prespecified categories (surface-CLEAN-but-structurally-descended,
    multi-step laundering) searched for directly across 4 derivation
    transforms and 5 depths and genuinely not found — reported as a
    finding (**zero observed laundering in the pilot corpus**), not a
    completion-count gap. Not phrased as "8/10" per correction below.
12. ~~Two open items from the worked-examples pass~~ — **RESOLVED
    2026-08-12, same session:** (a) `multi_hop_setup` CARRIES/REFERENCES
    boundary — froze the compositional-target rule (CARRIES requires
    asserting the *composed* proposition; juxtaposing premises without
    composing them is REFERENCES) in `docs/labeling_protocol.md`, and
    added a separate `derivation_contract_satisfied` field (structural
    on-contract vs. semantic composition are different questions).
    Relabeled worked example 6 from "borderline, leaning CARRIES" to
    REFERENCES accordingly. (b) oracle-vs-content divergence — corrected
    the `CO_RETRIEVED` definition (validates structural necessity under
    the authored contract, makes no claim about actual model behavior or
    content), introduced the three-layer framework (structural lineage /
    context exposure / semantic contamination), and rewrote H1/H2/H4
    above to recognize incidental context uptake as a real, observed
    second failure mode alongside over-tainting.
13. ~~My (Claude's) blind labeling could substitute for human κ~~ —
    **CORRECTED 2026-08-12: it cannot.** `docs/labeling_protocol.md`'s
    human-validation section now states explicitly that "human
    validation" requires an actual human; an AI blind-labeling pass is a
    legitimate supplementary `pipeline ↔ Claude` audit, never blended
    into or substituted for `pipeline ↔ human`.
14. ~~κ validation~~ — **RUN, REVISED, AND PASSED 2026-08-12.** 120-memory
    sample drawn (`eval/draw_kappa_sample.py`, stratified 6 per
    poison_form × depth), human blind-labeled it. **Run 1** (adjudicator
    could override the primary judge): κ=0.8103, raw agreement 89.2% —
    passed the gate, but surfaced that adjudication was net harmful (3
    fixes, 5 regressions out of 22 triggered). **Go/no-go decision:**
    NO-GO on stamping as-is; GO after making adjudication diagnostic-only
    (never overrides) and promoting the compositional-target rule to a
    standalone prompt instruction — rejected three narrower patches as
    either post-hoc overfitting to the exact observed error or
    inconsistent treatment across `poison_form`s. **Run 2** (final):
    recomputed on the *same* 120 samples (no new human labeling — stated
    transparently, this sample exists to calibrate/freeze the procedure)
    — **κ=0.8699, raw agreement 92.5%.** Every metric improved. Full
    reports: `results/kappa_sample/kappa_report.md` (final) and
    `kappa_report_v1_with_adjudication_SUPERSEDED.md` (superseded, kept
    for the record). Findings discussion: `docs/labeling_protocol.md`'s
    κ section.
15. ~~Re-commit as the timestamped pre-registration~~ — **DONE, this
    commit.** Per the go/no-go rule stated in advance: primary-only κ
    (0.8699) is ≥ 0.6, so this document is stamped, effective this
    commit. The REFERENCES-class weakness (P=0.75, R=0.46) is recorded as
    a preregistered limitation to report alongside aggregate κ (see the
    reporting language in `docs/labeling_protocol.md`), not grounds to
    keep iterating — doing so now would be calibration overfitting on the
    sample used to freeze the procedure.

**Status: STAMPED.** All three original blockers closed: Blocker A
(harness), Blocker B (worked examples, rubric frozen), Blocker C (κ
validation, revised once for a real cause, passed with margin on the
final design). Data generation is unblocked as of this commit.

16. ~~Full-run sample size / replication (§4)~~ — **RESOLVED 2026-08-12,
    same day as the stamp, as a scaling decision under the already-stamped
    design, not a reopening of it.** Seeds 3→5 (within-scenario noise
    reduction only, justified by confirmed `temperature=0` API
    non-determinism), effective inferential n remains 24 (scenario_id,
    the bootstrap unit), pooled-across-24 estimates set as primary for
    H1–H4 with `poison_form` panels (n=6) as descriptive/exploratory only.
    Full record and the SE arithmetic behind it: §4. No sample-size
    decision remains open. Generation may proceed.
