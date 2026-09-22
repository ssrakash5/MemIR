# Clean-control scenario review (2026-09-21)

The 6 `clean_control` scenarios (added 2026-08-15 as the false-positive
baseline, see `docs/preregistration.md`'s dated note) were authored solo
overnight and, until now, only mechanically verified (no
entity/number/identifier from `semantic_target` appears in
`source_facts` or `distractor_pool` — the counterfactual test fails for
every fact by construction, B_true=0). They had not had the human review
pass the original 24 scenarios received (`configs/scenarios/README.md`).

## Status: all 6 reviewed by the user, 3 revised, corpus now frozen

Review checked each scenario against the same five failure modes the
original 24's review used: lexical/topical proximity, target plausibility
vs. actual contamination, benign-content sanity, `true_parents`/
`derivation_plan` correctness, and prompt-style/domain balance.

**No case of actual contamination was found** — no benign fact anywhere
restates the harmful `semantic_target`, and all `true_parents`/
`derivation_plan` mappings are structurally correct (`child_1` → `P1`,
`child_2` → `B2`, per `clean_control_01.yaml`'s header rationale). The
issue found was narrower: some benign facts shared enough vocabulary with
their scenario's harmful `semantic_target` that an automated judge could
plausibly over-classify a derived memory as REFERENCES even though CARRIES
is impossible by construction — a false-positive risk to the false-positive
baseline itself, not a labeling-correctness bug.

| Scenario | Finding | Action taken |
|---|---|---|
| `clean_control_01` | Mild proximity (B1 "Expense reports ... are due" echoes the target's object) | Kept as-is — judged an acceptable, realistic clean-domain control |
| `clean_control_02` | Clean | Kept as-is |
| `clean_control_03` | Strong proximity (B1 repeated "Tracking numbers," the target's central object) | **Revised**: B1 text and `semantic_unit` changed to a delivery-status-cadence fact that doesn't repeat "tracking numbers" |
| `clean_control_04` | Moderate proximity ("conference room" vocabulary repeated across distractors) | Kept as-is — target's meaningful premise (standing authorization) isn't echoed by any source fact |
| `clean_control_05` | Strong proximity (B1 paired "inspected" + "safety," both concepts in the target) | **Revised**: B1 text and `semantic_unit` changed to a preventive-maintenance-review fact that drops both terms |
| `clean_control_06` | Strong proximity (B2's "sent ... after a ticket is closed" mirrors the target's post-closure-transmission structure) | **Revised**: B2 text and `semantic_unit` changed to an aggregate-reporting fact that drops the post-closure-transmission shape |

`prompt_style` assignment (terse→verbose→structured→terse→verbose→structured
across `_01`–`_06`, globally 2/2/2 balanced but not pairwise-matching the
original 24's `_01/_02`/`_03/_04`/`_05/_06` convention) was reviewed and
explicitly left as-is — global balance was judged sufficient, and matching
the pairwise convention exactly was not worth an additional frozen-corpus
edit.

## What changed, mechanically

- `clean_control_03.yaml`: `B1.text` and `B1.semantic_unit`
  (`tracking_update_cadence` → `delivery_status_cadence`). `B1` is not
  referenced by any `derivation_plan` entry, so no other field needed
  updating.
- `clean_control_05.yaml`: `B1.text` and `B1.semantic_unit`
  (`inspection_cadence` → `maintenance_review_cadence`). Same — `B1`
  unused elsewhere in the file.
- `clean_control_06.yaml`: `B2.text` and `B2.semantic_unit`
  (`satisfaction_survey` → `service_quality_reporting`), **and**
  `derivation_plan.depth_1.child_2.target_semantics` updated to match,
  since `_06` (unlike `_03`/`_05`) maps `child_2`'s `true_parents` to
  `B2` directly.

No `entities`, `poisoned` source facts, `distractor_pool` entries (other
than the B1/B2 edits above), or `true_parents` assignments were touched.

## Freeze status

With this review complete, the 6 `clean_control` scenarios join the
original 24 as part of the frozen scenario corpus — further changes
require a recorded, dated deviation and re-validation, consistent with
`docs/preregistration.md`'s freeze protocol.
