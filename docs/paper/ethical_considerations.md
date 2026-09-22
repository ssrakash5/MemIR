<!-- Optional per the SaTML checklist ("Ethical Considerations (optional):
May include discussion of ethical risks and mitigation strategies").
Does not count toward the page limit. Drafted 2026-09-09, grounded in
what this project actually did -- no new claims beyond threat_model.md,
method.md, and corpus_card.md. -->

# Ethical Considerations

**No real systems, users, or data are attacked.** All 30 scenarios are
synthetic: hand-authored specifications with LLM-generated surface
text (Section~[Method]), not real production agent-memory traces. No
deployed agent, real user account, or real document was targeted or
compromised to produce this corpus.

**Our poison-injection techniques are not novel attack contributions.**
The four `poison_form` styles we use to construct scenarios
(`direct_instruction`, `embedded_fact`, `authoritative_framing`,
`multi_hop_setup`) are simple content-injection patterns consistent
with attack classes already published and analyzed in prior work we
cite (MPBench's attack taxonomy, AgentPoison, MINJA). We do not
contribute a new poisoning technique, a new trigger-optimization
method, or any capability that lowers the bar for a real attacker
beyond what is already public. The contribution is a measurement
framework and defensive metric, applied against a known-compromise
precondition (Section~[Threat Model]).

**The primary contribution is defensive.** Blast-radius reconstruction,
attribution thresholding, and depth-aware containment are all analysis
and mitigation tools for an operator who has already detected a
compromise, not offensive techniques. To the extent our results
identify a weakness (e.g. the small but real laundering rate in H3, or
`CO_RETRIEVED` under-detection in H1), they identify weaknesses in
*defensive* provenance mechanisms, motivating better defenses, not new
attacks on real systems.

**Released artifacts do not increase attack capability.** The scenario
specifications, generation harness, and labeling pipeline we release
(Open Science) operate only on our own synthetic corpus and require an
attacker to already have the capability MemSecBench, MemLineage, and
MINJA already document as their starting threat model (influence over
content entering an agent's write path). Releasing our harness does
not provide a novel means of gaining that access.

**Dual-use consideration.** Any published work characterizing where
provenance-based defenses fail (H1's inflation growth, H2's recall
cost under thresholding, H3's laundering rate) could in principle
inform an adversary about which derivation transforms or fan-out
regimes are least likely to be caught. We judge the operational
disclosure risk here to be low relative to the defensive value: our
findings do not reveal a new attack, only quantify existing,
previously-known failure modes (e.g. MPBench and MemLineage already
discuss detection-strength gradients and attribution-threshold
tradeoffs) with more precision than prior work. We are not aware of a
responsible-disclosure obligation here, since no deployed system or
vendor-specific vulnerability is implicated — our findings are about
the general mechanics of derivation provenance, not a flaw in any
named product.
