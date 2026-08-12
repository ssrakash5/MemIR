# Pre-registration

**Status: skeleton draft, NOT the committed pre-registration.** Updated
2026-08-11 (third revision, same day) to match the finalized scenario
design in `configs/experiment_grid.yaml`: 24 `scenario_id`s (4
`poison_form` × 6 independent scenarios each) as the real
sampling/bootstrap unit, `prompt_style` demoted to a balanced per-scenario
attribute, and oracle authoring resolved to programmatic generation from a
human-approved scenario spec. `depth`/`attribution_threshold` remain
analysis-time factors, now validated by `spike/06_prefix_property.py`
(GREEN). **All 24 scenario specs are now HUMAN-APPROVED** (4 pilot,
approved 2026-08-11; 20 more, drafted and reviewed 2026-08-12 — 12
approved as drafted, 8 revised for semantic-target wording and
distractor/clean-sibling contamination, zero `true_parents` errors found
— see `configs/scenarios/README.md` for full detail). Also RESOLVED
2026-08-12: the automated labeler pipeline (LLM-primary + NLI
verification + adjudication, marker tokens excluded from the label
decision — see `docs/labeling_protocol.md`). Also done 2026-08-12: a v1
`eval/` generation harness (scoped to labeling validation, not the full
production sweep — see `CLAUDE.md` and `eval/README.md`), run
successfully (48 real traces, 480+ derived memories), and 8/10 labeling
worked examples built from that real output (2 categories genuinely
searched for and not found — a reportable finding, see
`docs/labeling_protocol.md`). **Status: BLOCKED** — see the closing
section below for the authoritative blocker list. κ validation has not
been run, and two scientific-framing questions surfaced by the worked
examples need resolution before the rubric can be frozen. Sample sizes
below still need real numbers plugged in.
**Do not generate experiment data against this version.**

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

- **Generation factors** (each combination produces one real trace —
  expensive): `scenario_id` (24 values: 4 `poison_form` × 6
  independently-constructed scenarios each — the real sampling unit, see
  §4/§5), `top_k` {1,3,5,10}, `write_fanout` {1,2,3}, `derivation_transform`
  (4 values, matching MemLineage §5.3's summarize/paraphrase/refine/continue
  vocabulary), `seeds` {0,1,2}. `prompt_style` (terse/verbose/structured —
  renamed from `summarization_prompt`) is a **balanced per-scenario
  attribute** (2 of each style's 6 scenarios get each `prompt_style` value),
  not a crossed factorial axis. **3,456 generated traces**
  (24×4×3×4×3).
- **Analysis factors** (computed post-hoc from a trace's persisted
  `(parent, child, attribution_score, run_id)` edges, no re-generation
  needed): `depth` {0..5}, `attribution_threshold` {null, 0.5, 0.7, 0.85},
  `containment_policy` {flat_transitive, depth_aware}. **82,944 depth ×
  threshold analysis cells** derivable from the 3,456 traces (3,456×6×4);
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

**Still not fully determined:**
- The distractor-per-run design (how many true parents vs. distractors per
  retrieval within each scenario's `distractor_pool` — this directly sets
  how hard the precision problem is, so it needs to be a deliberate
  choice per scenario, not incidental).
- ~~The pilot's 4 scenario specifications don't exist yet~~ — **done and
  HUMAN-APPROVED 2026-08-11** (`configs/scenarios/pilot/`). The remaining
  20 (5 more per `poison_form`) still need to be written before the full
  24-scenario generation run.
- Target scale from `docs/labeling_protocol.md`: ≥200 injection instances
  across ≥4 styles, chains to depth ≥3 — a floor for the *labeling
  validation* corpus specifically, distinct from and smaller than the
  24-scenario / 3,456-trace generation design (see that document's
  clarification of this distinction).

## 5. Statistics

- Paired bootstrap, 10,000 resamples, for all point estimates.
- 95% confidence intervals on every reported number.
- Wilcoxon signed-rank test for paired comparisons.
- **Bootstrap resampling unit is `scenario_id`, stratified by
  `poison_form`, not raw factorial cells or trace rows** — seeds
  within one scenario are nested repeated measurements, not independent
  samples; resampling 3,456 trace rows as though independent would be
  pseudo-replication.
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
14. **Still open, the one real remaining blocker:** κ validation hasn't
    been run at all. The rubric is now frozen (items 12a/12b resolved)
    and the harness output exists to draw the 100–150 memory sample
    from — but the sample hasn't been drawn, and a human still needs to
    do the blind labeling (not delegable, see item 13).
15. Once κ validation passes, re-commit with a note marking it as the
    actual pre-registration timestamp; no data generation before that
    commit.

**Status: BLOCKED, one blocker remaining (down from three).** Blocker A
(harness) — closed. Blocker B (worked examples) — closed (8 observed + 2
honestly-not-found, rubric frozen). Blocker C (κ validation) — still
fully open, and now unambiguously the critical path: rubric is frozen, so
this can start as soon as a human draws and blind-labels the sample.
Everything else in this document can continue in parallel, but per the
original agreed ordering: none of it clears the scientific gate on its
own.
