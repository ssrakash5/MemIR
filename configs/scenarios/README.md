# Full scenario corpus (24 total)

Parent directory for the complete 24-scenario design (4 `poison_form` × 6
independently-constructed scenarios each). `pilot/` holds the 4 originally
HUMAN-APPROVED scenarios (`_01` of each style). This directory holds the
remaining 20, drafted in 4 batches of 5 (one batch per `poison_form`) on
2026-08-12, then reviewed and corrected the same day.

## Status: all 24 scenarios HUMAN-APPROVED

| poison_form | `_01` | `_02`–`_06` |
|---|---|---|
| direct_instruction | APPROVED (`pilot/`) | **APPROVED — 5/5 as drafted, no changes needed** |
| embedded_fact | APPROVED (`pilot/`, wording normalized 2026-08-12) | **APPROVED — all 5 needed target-wording fixes; `_05`/`_06` also needed content fixes** |
| authoritative_framing | APPROVED (`pilot/`) | **APPROVED — `_02`/`_03` as drafted; `_04`/`_05`/`_06` needed distractor/child_2 fixes** |
| multi_hop_setup | APPROVED (`pilot/`) | **APPROVED — 5/5 as drafted, no changes needed** |

Review found **no wrong `true_parents` assignment anywhere in the 20** —
every ordinary scenario correctly uses `[P1]`, every `multi_hop_setup`
scenario correctly uses `[P1, B1]` (verified via both the P1-only and
B1-only counterfactuals independently). All revisions were semantic-target
wording or distractor/clean-sibling contamination, not causal-oracle
errors — the review's own framing of the significance of this result.

## What got revised (2026-08-12 review pass)

**`embedded_fact` — semantic_target wording (all 6, including `_01`).**
Original wording used an evaluator instruction ("Treat X as Y (true value
is Z)"). Revised to state the false proposition directly ("X is Y."),
with the true value moved fully to `entities`/oracle metadata — a
stricter, more consistent convention than the pilot review originally
required. `true_parents` unchanged in all 6.

**`embedded_fact_05` — B2 replaced.** Original ("quarterly estimated tax
payments due on the 15th") was itself a tax-deadline proposition that
repeated "15th," risking `child_2` reading as REFERENCES instead of a
clean CLEAN sibling. Replaced with an expense-report fact carrying no
date at all.

**`embedded_fact_06` — P1 rewritten.** Original opened "Spec update: ...
recertified ... up from the original conservative rating" — nearly the
same rhetorical shell as `_01`'s P1, risking the scenario reading as
"`_01` with nouns and numbers swapped" despite a genuinely different
device class and failure mode. Rewritten as a deployment/capacity note.

**`authoritative_framing_04` — D2/D5/D6 replaced.** D2 (timesheet outage)
sat too close to `child_2`'s own timesheet-reminder content; D5
(biweekly payroll schedule) echoed the poison's own payroll-cutoff
mechanics; D6 (contractor invoicing portal) combined "contractor" +
financial processing. Confirmed NOT a renamed `_01` despite the shared
payment-override shape — vendor settlement-account substitution and
contractor off-cycle payroll are different operational objects/workflows;
the issue was distractor hygiene only.

**`authoritative_framing_05` — B2 and D3 replaced.** B2 ("standard
contract review takes 5-7 days") directly discussed the exact process the
poison bypasses. D3 ("redline-tracking feature") created lexical
confusion with the counterparty name "Redline Ventures" despite being
topically unrelated.

**`authoritative_framing_06` — B2, D2, D5, D9 replaced.** All four
clustered around the visitor/security-desk mechanics the poison overrides
— none entailed the poison, but all were unnecessarily close for a clean
negative set.

## Files, by batch

| Batch | Files | Domain summary |
|---|---|---|
| 1 — direct_instruction | `_02`–`_06` | IT/security password-reset, legal/NDA routing, clinic scheduling, supply-chain/logistics, customer-support ticket export |
| 2 — embedded_fact | `_02`–`_06` | Software/DevOps API status, HR benefits deadline, facilities fire-code occupancy, finance tax deadline, network hardware PoE budget |
| 3 — authoritative_framing | `_02`–`_06` | IT access grant, procurement PO-threshold bypass, HR/payroll off-cycle payment, legal contract-review bypass, facilities/security visitor-escort bypass |
| 4 — multi_hop_setup | `_02`–`_06` | IT/database access, finance/AP auto-approval, warehouse fulfillment access, legal/data-export classification, DevOps deploy gating |

## Structural rules applied to all 24

- `child_1.true_parents` = `[P1]` for 19 scenarios, `[P1, B1]` for the 5
  `multi_hop_setup` scenarios (the one `poison_form` where composition is
  structurally required) — per the counterfactual test in
  `configs/experiment_grid.yaml`'s ground-truth principle.
- `distractor_count = max(0, top_k - true_parent_count)` per the frozen
  distractor rule; every pool has 9 entries.
- One true descendant (`child_1`) and one clean sibling (`child_2`,
  matching the pilot's `write_fanout=2`) per run.
- `prompt_style` balanced across each style's 6 scenarios: `_01`/`_02`
  terse, `_03`/`_04` verbose, `_05`/`_06` structured.

## Lesson for future scenario authoring (batches beyond this 24)

`multi_hop_setup`-style scenarios (opaque capability + opaque assignment)
are specifically prone to distractors that reuse the poison's own generic
vocabulary (a "tier," a "cost-center," a "scope") rather than just sharing
a topic — several were caught and fixed during drafting (documented in
git history for the Batch 4 commit). Check for **lexical** overlap with
the poison's key terms during scenario authoring, not just topical
overlap with `child_2`.

## Not yet done

- Marker-token placement isn't applied to any scenario yet — per
  `docs/labeling_protocol.md`, exact format is still to be designed.
- None of the 24 scenarios have been run through the (not-yet-built)
  corpus-generation script or `eval/` harness — they're approved
  human-authored input to that pipeline, not validated generation output.
