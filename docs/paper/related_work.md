<!-- DRAFT — Markdown first. Sourced from docs/prior_art.md and
docs/positioning.md's validated (full-read-verified) content; do not
re-extract from second-hand summaries when converting to LaTeX. -->

# Related Work

## Persistent-memory poisoning as a threat class

OWASP's Agentic Security Initiative names cross-session memory
poisoning as a distinct threat category (ASI06), separate from
single-turn prompt injection precisely because the compromised state
persists and can influence multiple future interactions. A cluster of
recent work — MemLineage, MemAudit, MemSecBench, MPBench, AgentPoison,
and MINJA — has established this as an active subfield within months.
We position our contribution against all six.

## Preventive lineage enforcement: MemLineage

MemLineage (arXiv 2605.14421) builds a lineage-guided enforcement
system: a cryptographic chain-of-custody layer plus an LLM-mediated
derivation-lineage DAG (module M4). M4 records an edge $(p \to c)$
whenever parent memory $p$ was present in the LLM's context when child
memory $c$ was written — execution/derivation provenance, not lexical
or cryptographic matching, and the paper states this is specifically
designed to survive paraphrasing and summarization. Three attribution
mechanisms weight parent→child edges (Coarse: uniform weight 1.0,
maximum recall/minimum precision; LmSelfEval: LLM-judged semantic
influence; AttnAttr: white-box attention attribution), and the
guarantee that an untrusted label reaches a downstream chain tip is
*conditional* on every edge on the path exceeding an attribution
threshold $\tau$ — MemLineage's own $\tau \times K$ sweep and $r_K$
metric (strong-edge recall at chain length $K$) study exactly this
degradation. Their evaluation is a deterministic scripted-judge harness
plus live runs on two models, evaluated primarily over **linear**
derivation chains, answering: does a critical ancestry path remain
detectable, so that a sensitive-action gate can catch it, as
attribution threshold and depth vary?

Our work sits downstream of a different trigger condition. MemLineage
asks whether an untrusted label survives *forward* to gate a *future*
action, before harm occurs. We ask: given a memory that is *already
known* to be compromised, what is the actual shape of its downstream
footprint in a **branching** graph (multiple derived memories per
retrieval event, not one), and what does reconstructing and containing
that footprint cost? MemLineage's Coarse attribution mode acknowledges
the precision/recall tradeoff we study exists, but does not
characterize it under branching write fan-out the way we do (H1), and
its evaluation does not construct or measure a blast-radius
precision/recall/inflation triple against ground-truth semantic
contamination the way our metrics do.

## Post-hoc attribution: MemAudit

MemAudit (arXiv 2605.23723) operates after a harmful event has already
been observed: given a defined harmful event $e = (q^*, y^*, R^*)$, it
combines a counterfactual memory-influence score with a structural
memory-consistency graph to rank suspicious memories for targeted
removal. Evaluated on MINJA QA and RAP/WebShop tasks across three
models, it reduces attack success rate to zero at low-to-moderate
contamination ratios, with a sharp operating-boundary transition (QA:
$\rho{=}0.20 \to$ 0% ASR-after, $\rho{=}0.25 \to$ 60–70%; RAP:
$\rho{=}0.15 \to$ 0%, $\rho{=}0.24 \to$ 80–87%) rather than gradual
degradation. Critically, MemAudit does **not** maintain persistent
derivation provenance connecting a known-compromised source to
downstream writes independent of replaying each harmful event — its
memory-consistency graph is a semantic *consistency* graph, not a
derivation *lineage* graph, and its own limitations section states
undetected failures cannot be repaired by the system.

We do not claim MemAudit cannot handle laundered content that is
itself later retrieved for a harmful event (its counterfactual replay
and anomaly detection may still catch such cases). The defensible
distinction is structural: MemAudit requires an observed harmful
signal to trigger investigation; we study reconstructing exposure from
a known-compromised *source*, independent of whether any downstream
write has yet caused visible harm.

## Lifecycle benchmarking: MemSecBench

MemSecBench (arXiv 2607.27080) is the closest match in evaluation
*methodology*, though not in research question. It traces a linked
Write→Execute→Forget lifecycle anchored to a case-specific
`target_memory_manifest` describing malicious semantics, evaluated
across 310 linked test cases, 2 agent harnesses, 3 LLM backends, and 4
memory backends. It measures whether malicious semantics persist
(84.2% configuration-macro-averaged persistence), complete an
end-to-end Write→Execute chain (50.3%), and can be selectively repaired
without damaging benign memory (56.1% joint success, vs. 86.3% for
target-removal alone) — the gap between those last two figures is
direct independent evidence that collateral damage to benign memory,
not detection, is repair's hard part, which motivates our own
`inflation_ratio`/`containment_cost` metrics. MemSecBench does not
construct a derivation-lineage graph, does not track which *other*
memories become descendants of a compromised one, and does not measure
blast-radius precision/recall under branching retrieval/write
fan-out — it is semantic lifecycle tracking, not structural
provenance. We also adopt its case-construction precedent (structured
scenario authoring, human review gate, ground truth anchored to a
single semantic-target definition per case) for our own scenario corpus.

## Attack taxonomy and detection-strength gradient: MPBench

MPBench (arXiv 2606.04329v2 — distinct from an unrelated same-named
paper, arXiv 2503.12505, which we do not cite) evaluates a 6-class
attack taxonomy (Explicit Command Insertion, Conditional Command
Insertion, Salience-Driven Compaction Poisoning, Policy-Conformant Fact
Injection, False Precedent Insertion, Skill-Procedure Insertion) across
3,240 adversarial and 2,997 benign cases, two agents, seven domains.
Our `poison_form` axis is *not* this taxonomy — only
`direct_instruction` and partially `embedded_fact`/
`authoritative_framing` overlap it; `multi_hop_setup` is our own
construction. MPBench's strong/weak-signal distinction (e.g. a prompt-
injection detector, PromptArmor, dropping from 84.44% to 42.50%
detection between strong- and weak-signal payloads) independently
motivates our H3 surface-vs-execution-provenance comparison. MPBench's
Skill-Procedure Insertion finding also shows downstream
dependency/amplification through repeated execution is already
discussed in prior work — we do not claim to be first to observe that
poison can compound downstream, only that no prior work constructs or
evaluates a structural derivation graph, reconstructs blast radius from
a known-compromised root, or measures over-tainting under branching
fan-out the way we do. MPBench itself recommends write-path provenance
tracking as a defense direction, so provenance tracking per se is not
our novelty claim.

## Attack-construction work: AgentPoison and MINJA

AgentPoison (arXiv 2407.12784) and MINJA (arXiv 2503.03704) are
attack-construction papers on a different object than ours. AgentPoison
uses constrained-optimization trigger generation to map triggered
queries to a compact embedding region, achieving ~82% average
poisoned-retrieval success (ASR-r) and ~63% end-to-end attack success
(ASR-t) across three agent settings, but assumes an attacker with
white-box retriever access and the ability to directly inject
key-value pairs into the memory store — a stronger capability
assumption than ours. MINJA achieves ~98.2% injection success and
~76.8% attack success by having the attacker behave as an ordinary
user (no direct memory access), via bridging steps and progressive
query shortening, but its main threat model assumes a *shared* memory
bank across users, and its empirical results are not validated for
isolated per-user memory. Neither paper constructs or evaluates a
downstream derivation graph, blast-radius precision/recall, or
containment cost after compromise is known. We do borrow MINJA's
methodological observation that attack-instance content variation
(they use 9 independent victim-target pairs) matters more than
run-level stochasticity — independent support for our
`scenario_id`-based sampling design (Section [Method]).

## Summary

| | Trigger | Graph shape | Question |
|---|---|---|---|
| MemLineage | preventive (before action) | mostly linear chains | does ancestry survive to gate an action? |
| MemAudit | reactive (harm observed) | none (consistency graph, not lineage) | which memory caused *this* failure? |
| MemSecBench | lifecycle checkpoints | none (semantic manifest tracking) | does malicious semantics persist/propagate/repair? |
| **This work** | **known compromise (no harm required yet)** | **branching derivation graph** | **what is exposed downstream, and what does containment cost?** |

We do not claim priority on persistent-memory poisoning as a threat, on
provenance tracking as a mitigation mechanism, or on the observation
that poison can compound downstream through repeated execution — all
three are established or independently suggested by the papers above.
The contribution is the specific research object: post-incident
blast-radius reconstruction in **branching** agent-memory graphs, with
metrics (blast-radius precision/recall, inflation ratio, containment
cost) that none of the six papers above measure.
</content>
