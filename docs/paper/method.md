<!-- DRAFT — Markdown first. Source: configs/experiment_grid.yaml,
docs/labeling_protocol.md, docs/preregistration.md, src/memoryir/*.py.
This section should stay synchronized with those frozen artifacts, not
duplicate them by hand -- convert with direct reference where possible. -->

# Method

## Overview

We construct branching agent-memory derivation graphs under controlled
conditions, using a generation harness that enforces a fixed set of
mechanical rules (Section 3.1), on 30 hand-authored scenarios (24
poisoned across four `poison_form` styles, 6 unpoisoned controls,
Section 3.2), across three LLMs. Every derived memory is then labeled
against its scenario's ground-truth semantic target by a validated
three-signal automated pipeline (Section 3.3), and blast-radius metrics
are computed against a three-layer ground-truth framework that
separates structural lineage, context exposure, and semantic
contamination (Section 3.4).

## 3.1 Generation harness

**Provenance contract.** Every model call goes through a single
function (`generate_trace`, `src/memoryir/harness.py`); influence
edges are recorded at generation time from the scenario's approved
specification, not inferred after the fact — `STRUCTURAL_PARENT` edges
mark a write's declared true dependencies, `CO_RETRIEVED` edges mark
everything else present in the same shared retrieval context.

**Shared retrieval per run.** One retrieval event returns a `top_k`
set (true parents first, distractors filling remaining slots); *all*
`write_fanout` children produced in that run derive from the same
shared context. This is what makes `write_fanout` actually test
over-tainting rather than relabeling independent single-child runs:
naive coarse provenance would link every retrieved item to every child
written in the same run, producing exactly the false-positive source
H1/H2 measure.

**Focus/background prompt split.** Each derivation call is given its
structural parents as "primary notes to work from" and everything else
retrieved as background context explicitly marked off-topic — without
this distinction, an early build showed a "clean sibling" write would
spuriously blend in unrelated retrieved content, making it impossible
to construct genuine incidentally-exposed test cases.

**Depth-continuation rule.** The compromised root's structural lineage
(`child_1`) continues across depths (each depth's true parent is the
previous depth's `child_1`); sibling writes at each depth
(`child_2`, and `child_3` when `write_fanout=3`) are fresh,
distractor-seeded writes that do not continue their own lineage,
keeping the branching structure tractable while still exercising
co-retrieval fan-out at every depth. `child_3` (present only at
`write_fanout=3`) has no scenario-authored structural parent — no
scenario spec defines a third dependent — and is treated as a
distractor-only sibling at every depth by design.

**Cross-model generation.** Three backends implement an identical
`derive()` interface so the harness is agnostic to which model
produced a trace: gpt-4o-mini and gpt-4o (Azure OpenAI, same API
shape), and Llama-3.3-70B-Instruct (Azure AI Foundry, a distinct REST
API). The prompt construction is shared verbatim across all three — no
per-model prompt tuning — so cross-model comparisons are not confounded
by differential prompting.

## 3.2 Scenario corpus

**24 poisoned scenarios**, 6 independently-constructed instances per
`poison_form` (`direct_instruction`, `embedded_fact`,
`authoritative_framing`, `multi_hop_setup`) — the independent
construction matters: `poison_form` alone is not a valid sampling unit
if each style is a single hand-written payload merely regenerated
across seeds, which would measure only model stochasticity, not
generalization across independently constructed attack instances of a
style. `scenario_id` (not `poison_form`, not raw factorial cells) is
therefore the real sampling/inferential unit; bootstrap confidence
intervals resample at this level, stratified by `poison_form`.

**Oracle ground truth is programmatically generated from a
human-approved specification** — not hand-authored per edge, and not
left to an LLM to decide after the fact. A human approves each
scenario's semantics and declared true-dependency structure (applying
a counterfactual test: if a given parent fact were removed, could the
child still fully express the target semantics from the remaining
facts alone? if yes, that parent is not structurally necessary);
deterministic code then derives every oracle edge and node label from
that approved specification.

**6 clean/unpoisoned controls**, added specifically as a false-positive
baseline: no adversarial content anywhere, with a `semantic_target`
describing a plausible-sounding but never-injected harmful claim in an
analogous domain, verified non-composable from that scenario's own
source facts (no distinctive identifier overlap, only expected
topical-vocabulary overlap).

**`multi_hop_setup` compositional targets** require combining two
premises that individually establish nothing harmful — the
counterfactual test above genuinely requires two structural parents
only for this style; every other style's targets are established by a
single source fact (a second co-occurring fact is present but
`CO_RETRIEVED`, not structurally necessary).

## 3.3 Automated labeling

Two independent, deliberately un-conflated label layers:

1. **Content-level labels** (`CARRIES` / `REFERENCES` / `CLEAN`): does
   a derived memory's actual text assert the injected claim, merely
   reference it, or show no trace? For compositional targets, `CARRIES`
   requires asserting the full *composed* proposition — juxtaposing
   component premises without composing them is `REFERENCES`, not
   `CARRIES`, a rule frozen after real generation output surfaced a
   genuine boundary case.
2. **Structural/oracle labels** (`STRUCTURAL_PARENT` / `CO_RETRIEVED`
   edges; `TRUE_DESCENDANT` / `COEXPOSED` / `UNRELATED` node
   reachability): is a memory actually causally downstream of the
   compromised root, per the scenario's authored contract? Set at
   generation time from the approved specification, independent of
   whether the resulting text still asserts the claim.

The content-level labeler is LLM-primary: a single LLM judge (given
only the semantic target and candidate text, never scenario identity,
oracle labels, or marker status) produces the final label,
unconditionally. An independent NLI model and a second LLM
adjudicator run alongside it for diagnostic logging only — an earlier
design let the adjudicator override the primary judge on flagged
disagreements, but validation against a 120-sample human-labeled
calibration set showed this was net-harmful (it fixed 3 wrong labels
but broke 5 correct ones, concentrated in compositional-target cases),
so the adjudicator's role was demoted to diagnostic-only. **Validated
against blind human annotation: Cohen's $\kappa = 0.8699$ and, on an
independent rerun of the identical pipeline, $\kappa = 0.8838$** — both
comfortably clear the pre-registered $\kappa \geq 0.6$ gate; the
rerun's difference from the first (despite zero code changes) reflects
genuine `temperature=0` API non-determinism, not measurement error, and
both runs agree on the pipeline's one known weakness (REFERENCES-class
recall, concentrated in `multi_hop_setup`'s compositional boundary).
Marker-token detection is deliberately excluded from the label
decision — it is instead a separate H3 measurement (surface-marker
survival), and letting it influence the content label would make the
labeler manufacture the correlation H3 exists to discover.

## 3.4 Ground truth and metrics

**Three-layer framework**, distinguished because they can diverge —
real generation output produced a case where content merely
co-retrieved into a write's context (not a structural parent) still
surfaced in that write's actual semantic content:

- **Structural lineage** — reachability via `STRUCTURAL_PARENT` edges
  only (`TRUE_DESCENDANT`).
- **Context exposure** — reachability via any edge, structural or
  co-retrieved (conservative propagation).
- **Semantic contamination** — actual `content_label == CARRIES`, the
  ground truth blast-radius metrics are anchored to.

**$B_{true}$** = the set of memories with `content_label == CARRIES`
downstream of a compromised root (not structural reachability alone,
per the divergence above). **$B_{flagged}$** = whatever a given
detection policy flags, computed *without* access to content labels
(a real detector does not have ground truth):

$$P_{BR} = \frac{|B_{flagged} \cap B_{true}|}{|B_{flagged}|} \qquad
  R_{BR} = \frac{|B_{flagged} \cap B_{true}|}{|B_{true}|} \qquad
  \text{inflation} = \frac{|B_{flagged}|}{|B_{true}|}$$

reported as N/A, never coerced to zero, whenever $|B_{true}| = 0$.
Four detection policies are compared: **structural** (lineage-only),
**context\_exposure**/**flat\_transitive** (conservative, any edge —
these are the same policy under two names used by different
hypotheses), **thresholded** (context-exposure edges pruned by a
per-edge attribution score — operationalized as cosine similarity
between parent/child memory embeddings, since the frozen design named
an `attribution_threshold` factor without specifying a concrete score
to threshold), and **depth\_aware** (conservative propagation within a
bounded window of the compromised root, structural-only beyond it — an
explicit operationalization of the "one baseline, one proposed method"
containment comparison the frozen design named without an algorithm).
Traversal is implemented as plain breadth-first search over an
in-memory adjacency list (not a live recursive SQL query), validated
against a hand-built fixture with known answers — including a
deliberately cyclic graph confirming termination — before being run
against real data.

**Containment cost** ($C_{regen}$) counts unique generating runs that
would need to be replayed to regenerate a flagged set (one run
producing several exposed memories counts once, not per-object).

## 3.5 Experimental design

**Full factorial**: 30 scenarios × 3 models × 4 `top_k` values
(1/3/5/10) × 3 `write_fanout` values (1/2/3) × 4 `derivation_transform`
values (summarize/paraphrase/refine/continue) × 5 seeds = 21,600
generated traces. Seeds are a within-scenario noise-reduction measure
(justified by confirmed API non-determinism at `temperature=0`), not
additional statistical replicates — the true inferential unit remains
`scenario_id` (n=24 for the poisoned corpus, 6 per `poison_form`
stratum), so seed count does not increase statistical power. `depth`
(0–5) and `attribution_threshold` are analysis-time factors computed
post-hoc from a trace's persisted edges, not regeneration factors — no
new model calls are needed to sweep them, validated by a prefix-property
check (a depth-$d$ prefix of a depth-5 trace equals a trace generated
with `max_depth=d` directly).

**Reporting hierarchy:** pooled-across-24-scenario estimates are
primary for H1–H4; per-`poison_form` panels (n=6 each) are reported as
descriptive/exploratory only, never as independently-powered
comparisons — the effective sample size for a `poison_form`-level claim
is 6, not the hundreds of underlying trace rows beneath it.

**Statistics:** paired bootstrap (10,000 resamples, stratified by
`poison_form`) for every reported point estimate and 95% CI; Wilcoxon
signed-rank for paired policy comparisons at matched scenarios.
</content>
