<!-- DRAFT — synthesized from docs/paper/intro.md's contributions list and
docs/paper/results.md's summary; no new claims, only compression. -->

# Abstract

Persistent-memory poisoning, an attacker-influenced false or harmful
claim written into an LLM agent's long-term memory, is an established
cross-session security problem distinct from single-turn prompt
injection, because the compromised state outlives the triggering
interaction and can be *derived* into further memories through
summarization, paraphrase, or continuation. Prior work asks either
whether a poisoned label survives to gate a future action (preventive)
or how to rank suspicious memories after a harmful outcome is already
observed (reactive). We study a different, operationally realistic
moment: once a memory or source is *known* to be compromised,
independent of whether it has caused visible harm yet, how accurately
can execution provenance reconstruct its downstream blast radius in a
**branching** derivation graph, and what does containment cost, as a
function of retrieval fan-out, derivation depth, and attribution
policy?

We build a generation harness that produces branching derivation
graphs under controlled conditions across three LLMs (gpt-4o-mini,
gpt-4o, Llama-3.3-70B-Instruct), 30 scenarios (24 adversarial across
four poison-injection styles, 6 clean controls), yielding 21,570
generated traces and 216,319 labeled derived memories (Cohen's
$\kappa = 0.87$ to $0.88$ against blind human annotation). We
characterize a precision/recall frontier, not a single failure mode:
conservative provenance preserves near-complete recall but produces
growing false-positive inflation with retrieval fan-out and derivation
depth (H1); attribution thresholding reduces that inflation at a
measurable recall cost, pruning exactly the weakly-attributed edges
that are sometimes the only path to real contamination (H2); a harmful
claim's literal surface form survives rewording more reliably than a
naive marker-matching check would suggest, but not perfectly (a small,
0.79%, highly non-uniform, and model-dependent laundering rate persists
at full corpus scale) (H3); and a depth-aware containment policy
reduces over-quarantine by roughly 30% relative to a flat conservative
policy, at a quantifiable and cross-model-uneven missed-contamination
cost (H4). No single model is uniformly safer across all three failure
modes we measure, which is itself a result an incident-response
operator needs, not an artifact to be averaged away.
