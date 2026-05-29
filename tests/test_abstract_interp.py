"""Tests for abstract interpretation fixed-point analysis. 14 tests, 4 tiers."""
import json, os, sys
sys.path.insert(0, "/app/runtime")
STATE_PATH = "/app/runtime/lattice_state.jsonl"
REPORT_PATH = "/app/runtime/analysis_report.jsonl"

def load_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]

class TestTier1Structural:
    def test_output_files_exist(self):
        assert os.path.isfile(STATE_PATH) and os.path.isfile(REPORT_PATH)
    def test_point_count(self):
        assert len([s for s in load_jsonl(STATE_PATH) if "point_id" in s]) == 7
    def test_point_ids(self):
        ids = {s["point_id"] for s in load_jsonl(STATE_PATH) if "point_id" in s}
        assert ids == {"entry","loop_head","branch_t","branch_f","merge","handler","exit"}
    def test_vector_dimensions(self):
        for e in load_jsonl(STATE_PATH):
            if "lattice_vector" in e: assert len(e["lattice_vector"]) == 7
    def test_required_fields(self):
        for e in load_jsonl(STATE_PATH):
            assert {"point_id","lattice_vector","vector_sum"}.issubset(e.keys())
    def test_report_structure(self):
        types = {r.get("type") for r in load_jsonl(REPORT_PATH)}
        assert {"point_state","convergence_analysis","digest"}.issubset(types)

class TestTier2StateValues:
    def test_entry_own_height(self):
        state = load_jsonl(STATE_PATH)
        entry = next(s for s in state if s["point_id"] == "entry")
        # Sorted: branch_f(0),branch_t(1),entry(2),exit(3),handler(4),loop_head(5),merge(6)
        assert entry["lattice_vector"][2] == 14, (
            f"Entry own is {entry['lattice_vector'][2]}, expected 14. "
            f"JOIN operations must merge all components including own and increment.")
    def test_join_knowledge_transfer(self):
        state = load_jsonl(STATE_PATH)
        lh = next(s for s in state if s["point_id"] == "loop_head")
        # loop_head's entry-component (idx 2) should be 9 (absorbed from JOIN)
        assert lh["lattice_vector"][2] == 9
    def test_joined_vs_unjoined_sums(self):
        state = load_jsonl(STATE_PATH)
        entry = next(s for s in state if s["point_id"] == "entry")
        merge = next(s for s in state if s["point_id"] == "merge")
        assert entry["vector_sum"] >= 72
        assert merge["vector_sum"] == 27

class TestTier3PairClassification:
    def test_worklist_order_by_height(self):
        report = load_jsonl(REPORT_PATH)
        a = next(r for r in report if r["type"] == "convergence_analysis")
        assert a["worklist_order"][-1] == "entry", (
            f"Last in worklist is '{a['worklist_order'][-1]}', expected 'entry'.")
    def test_exact_converged_count(self):
        report = load_jsonl(REPORT_PATH)
        a = next(r for r in report if r["type"] == "convergence_analysis")
        assert a["converged_count"] == 14, (
            f"Converged count is {a['converged_count']}, expected 14.")
    def test_no_dominated_in_converged(self):
        report = load_jsonl(REPORT_PATH)
        a = next(r for r in report if r["type"] == "convergence_analysis")
        pairs = [tuple(p) for p in a["converged_pairs"]]
        forbidden = [("entry","merge"),("entry","handler"),("entry","exit"),
                     ("branch_t","merge"),("branch_t","exit"),
                     ("handler","merge"),("handler","exit")]
        for pair in forbidden:
            assert pair not in pairs and tuple(reversed(pair)) not in pairs
        assert ("loop_head","exit") in pairs or ("exit","loop_head") in pairs

class TestTier4Consistency:
    def test_report_digest(self):
        report = load_jsonl(REPORT_PATH)
        d = next(r for r in report if r["type"] == "digest")
        assert d["fingerprint"] == "c07bf80123c73e95"
    def test_state_report_cross_validation(self):
        state = load_jsonl(STATE_PATH)
        report = load_jsonl(REPORT_PATH)
        sm = {s["point_id"]: s for s in state}
        rm = {r["point_id"]: r for r in report if r.get("type") == "point_state"}
        assert len(sm) == len(rm) == 7
        for pid in sm:
            assert sm[pid]["lattice_vector"] == rm[pid]["lattice_vector"]
            assert sm[pid]["vector_sum"] == rm[pid]["vector_sum"]
