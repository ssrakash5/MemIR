"""Hand-built fixture with known answers, per week2.md's explicit rule:
metrics code must be validated against known-answer fixtures before any
real data touches it. Includes a deliberately cyclic graph to verify
reachable_from() terminates (week2.md's mandatory cycle test).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from memoryir.metrics import TraceGraph, b_flagged, b_true, blast_radius_metrics, reachable_from


def _fixture_graph() -> TraceGraph:
    # 1 = compromised root (depth 0, no content_label -- source facts aren't labeled)
    # 2 = child_1 d1, STRUCTURAL_PARENT from 1, CARRIES (true lineage, on-contract)
    # 3 = child_2 d1, CO_RETRIEVED from 1 (root merely co-retrieved), CLEAN
    # 4 = child_1 d2, STRUCTURAL_PARENT from 2, CARRIES (lineage continues)
    # 5 = child_2 d2, CO_RETRIEVED from 2, CARRIES (worked-example-8 pattern:
    #     incidental context leakage produces real contamination off the
    #     structural lineage)
    # 6 = CARRIES, but NO edge from root at all -- an unreachable
    #     contamination a detector should legitimately fail to catch
    #     (tests that R_BR can be < 1 for BOTH policies)
    nodes = {
        1: {"depth": 0, "branch": "source_fact", "content_label": None},
        2: {"depth": 1, "branch": "child_1", "content_label": "CARRIES"},
        3: {"depth": 1, "branch": "child_2", "content_label": "CLEAN"},
        4: {"depth": 2, "branch": "child_1", "content_label": "CARRIES"},
        5: {"depth": 2, "branch": "child_2", "content_label": "CARRIES"},
        6: {"depth": 1, "branch": "child_3", "content_label": "CARRIES"},
    }
    edges = [
        (1, 2, "STRUCTURAL_PARENT"),
        (1, 3, "CO_RETRIEVED"),
        (2, 4, "STRUCTURAL_PARENT"),
        (2, 5, "CO_RETRIEVED"),
    ]
    return TraceGraph(nodes=nodes, edges=edges, root_id=1)


def test_b_true():
    g = _fixture_graph()
    assert b_true(g, max_depth=2) == {2, 4, 5, 6}
    assert b_true(g, max_depth=1) == {2, 6}  # 4,5 excluded (depth 2 > horizon)


def test_structural_policy():
    g = _fixture_graph()
    flagged = b_flagged(g, policy="structural", max_depth=2)
    assert flagged == {2, 4}, flagged  # never reaches 3,5 (CO_RETRIEVED-only) or 6 (unreachable)

    m = blast_radius_metrics(g, policy="structural", max_depth=2)
    assert m["b_true_n"] == 4
    assert m["b_flagged_n"] == 2
    assert m["P_BR"] == 1.0   # {2,4} both truly CARRIES
    assert m["R_BR"] == 0.5   # misses 5 (incidental) and 6 (unreachable)
    assert m["inflation_ratio"] == 0.5


def test_context_exposure_policy():
    g = _fixture_graph()
    flagged = b_flagged(g, policy="context_exposure", max_depth=2)
    assert flagged == {2, 3, 4, 5}, flagged  # reaches 3 via CO_RETRIEVED too; still never 6

    m = blast_radius_metrics(g, policy="context_exposure", max_depth=2)
    assert m["b_true_n"] == 4
    assert m["b_flagged_n"] == 4
    assert m["P_BR"] == 0.75   # 3 is a false positive (CLEAN, flagged anyway)
    assert m["R_BR"] == 0.75   # catches 5 (the incidental-leakage case) but not 6
    assert m["inflation_ratio"] == 1.0

    # The central phenomenon this whole paper is about, reproduced exactly
    # in miniature: context-exposure trades precision for recall relative
    # to structural-only, on the SAME fixture.
    struct = blast_radius_metrics(g, policy="structural", max_depth=2)
    assert m["R_BR"] > struct["R_BR"]
    assert m["P_BR"] < struct["P_BR"]


def test_empty_b_true_is_none_not_zero():
    g = TraceGraph(
        nodes={1: {"depth": 0, "branch": "source_fact", "content_label": None},
               2: {"depth": 1, "branch": "child_1", "content_label": "CLEAN"}},
        edges=[(1, 2, "STRUCTURAL_PARENT")],
        root_id=1,
    )
    m = blast_radius_metrics(g, policy="structural", max_depth=1)
    assert m["P_BR"] is None
    assert m["R_BR"] is None
    assert m["inflation_ratio"] is None


def test_depth_horizon_excludes_deeper_nodes():
    g = _fixture_graph()
    m0 = blast_radius_metrics(g, policy="context_exposure", max_depth=1)
    assert m0["b_true_n"] == 2  # only {2, 6}, node 4/5 excluded at depth>1
    assert m0["b_flagged_n"] == 2  # {2, 3}


def test_thresholded_policy_prunes_weak_edges():
    g = _fixture_graph()
    scores = {(1, 2): 0.9, (1, 3): 0.6, (2, 4): 0.9, (2, 5): 0.4}
    g_scored = TraceGraph(nodes=g.nodes, edges=g.edges, root_id=g.root_id, edge_scores=scores)

    # threshold=0.7 keeps only (1,2) and (2,4) -- same reachable set as "structural"
    flagged_hi = b_flagged(g_scored, policy="thresholded", max_depth=2, threshold=0.7)
    assert flagged_hi == {2, 4}, flagged_hi

    # threshold=0.5 additionally keeps (1,3) but still prunes (2,5)
    flagged_mid = b_flagged(g_scored, policy="thresholded", max_depth=2, threshold=0.5)
    assert flagged_mid == {2, 3, 4}, flagged_mid

    # threshold=0.0 keeps everything -- same reachable set as context_exposure
    flagged_lo = b_flagged(g_scored, policy="thresholded", max_depth=2, threshold=0.0)
    assert flagged_lo == {2, 3, 4, 5}, flagged_lo


def test_thresholded_missing_score_is_pruned_not_kept():
    g = _fixture_graph()
    g_scored = TraceGraph(nodes=g.nodes, edges=g.edges, root_id=g.root_id, edge_scores={})
    flagged = b_flagged(g_scored, policy="thresholded", max_depth=2, threshold=0.1)
    assert flagged == set(), flagged  # every edge missing a score -> pruned, not defaulted-open


def test_cycle_terminates():
    """week2.md's mandatory cycle test: a deliberately cyclic graph must
    not hang reachable_from()."""
    nodes = {
        1: {"depth": 0, "branch": "source_fact", "content_label": None},
        2: {"depth": 1, "branch": "child_1", "content_label": "CARRIES"},
        3: {"depth": 2, "branch": "child_1", "content_label": "CARRIES"},
    }
    # 1 -> 2 -> 3 -> 2 (cycle between 2 and 3)
    edges = [
        (1, 2, "STRUCTURAL_PARENT"),
        (2, 3, "STRUCTURAL_PARENT"),
        (3, 2, "STRUCTURAL_PARENT"),
    ]
    from memoryir.metrics import build_adjacency
    adj = build_adjacency(edges, {"STRUCTURAL_PARENT"})
    result = reachable_from(1, adj)  # must terminate
    assert result == {2, 3}, result


def test_negative_control_cycle_reachability_is_correct():
    """Not just 'doesn't hang' -- also confirms the visited-set logic
    doesn't silently drop or duplicate nodes under a cycle."""
    nodes = {1: {}, 2: {}, 3: {}, 4: {}}
    edges = [(1, 2, "R"), (2, 3, "R"), (3, 2, "R"), (3, 4, "R")]
    from memoryir.metrics import build_adjacency
    adj = build_adjacency(edges, {"R"})
    assert reachable_from(1, adj) == {2, 3, 4}


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\nAll {len(tests)} fixture tests passed.")
