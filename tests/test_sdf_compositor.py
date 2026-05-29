"""Tests for SDF ray marching compositor. 14 tests, 4 tiers."""
import json, os, sys
sys.path.insert(0, "/app/runtime")
STATE_PATH = "/app/runtime/sdf_state.jsonl"
REPORT_PATH = "/app/runtime/render_report.jsonl"

def load_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]

class TestTier1Structural:
    def test_output_files_exist(self):
        assert os.path.isfile(STATE_PATH) and os.path.isfile(REPORT_PATH)
    def test_prim_count(self):
        assert len([s for s in load_jsonl(STATE_PATH) if "prim_id" in s]) == 7
    def test_prim_ids(self):
        ids = {s["prim_id"] for s in load_jsonl(STATE_PATH) if "prim_id" in s}
        assert ids == {"sphere_a","box_b","torus_c","cone_d","capsule_e","cylinder_f","plane_g"}
    def test_vector_dimensions(self):
        for e in load_jsonl(STATE_PATH):
            if "sdf_vector" in e: assert len(e["sdf_vector"]) == 7
    def test_required_fields(self):
        for e in load_jsonl(STATE_PATH):
            assert {"prim_id","sdf_vector","vector_sum"}.issubset(e.keys())
    def test_report_structure(self):
        types = {r.get("type") for r in load_jsonl(REPORT_PATH)}
        assert {"prim_state","occlusion_analysis","digest"}.issubset(types)

class TestTier2StateValues:
    def test_sphere_own_distance(self):
        state = load_jsonl(STATE_PATH)
        sa = next(s for s in state if s["prim_id"] == "sphere_a")
        # Sorted: box_b(0),capsule_e(1),cone_d(2),cylinder_f(3),plane_g(4),sphere_a(5),torus_c(6)
        assert sa["sdf_vector"][5] == 14, (
            f"sphere_a own SDF is {sa['sdf_vector'][5]}, expected 14. "
            f"BLEND must include own component in merge and increment after.")
    def test_blend_knowledge_transfer(self):
        state = load_jsonl(STATE_PATH)
        bb = next(s for s in state if s["prim_id"] == "box_b")
        # box_b's sphere_a-component (idx 5) should be 9 (absorbed from BLEND)
        assert bb["sdf_vector"][5] == 9
    def test_blended_vs_unblended_sums(self):
        state = load_jsonl(STATE_PATH)
        sa = next(s for s in state if s["prim_id"] == "sphere_a")
        ce = next(s for s in state if s["prim_id"] == "capsule_e")
        assert sa["vector_sum"] >= 72
        assert ce["vector_sum"] == 27

class TestTier3PairClassification:
    def test_render_order_by_distance(self):
        report = load_jsonl(REPORT_PATH)
        a = next(r for r in report if r["type"] == "occlusion_analysis")
        assert a["render_order"][-1] == "sphere_a", (
            f"Last in render order is '{a['render_order'][-1]}', expected 'sphere_a'.")
    def test_exact_independent_count(self):
        report = load_jsonl(REPORT_PATH)
        a = next(r for r in report if r["type"] == "occlusion_analysis")
        assert a["independent_count"] == 14, (
            f"Independent count is {a['independent_count']}, expected 14.")
    def test_no_dominated_in_independent(self):
        report = load_jsonl(REPORT_PATH)
        a = next(r for r in report if r["type"] == "occlusion_analysis")
        pairs = [tuple(p) for p in a["independent_pairs"]]
        forbidden = [("sphere_a","capsule_e"),("sphere_a","cylinder_f"),("sphere_a","plane_g"),
                     ("torus_c","capsule_e"),("torus_c","plane_g"),
                     ("cylinder_f","capsule_e"),("cylinder_f","plane_g")]
        for pair in forbidden:
            assert pair not in pairs and tuple(reversed(pair)) not in pairs
        assert ("box_b","capsule_e") in pairs or ("capsule_e","box_b") in pairs

class TestTier4Consistency:
    def test_report_digest(self):
        report = load_jsonl(REPORT_PATH)
        d = next(r for r in report if r["type"] == "digest")
        assert d["fingerprint"] == "eb349cdee629424d"
    def test_state_report_cross_validation(self):
        state = load_jsonl(STATE_PATH)
        report = load_jsonl(REPORT_PATH)
        sm = {s["prim_id"]: s for s in state}
        rm = {r["prim_id"]: r for r in report if r.get("type") == "prim_state"}
        assert len(sm) == len(rm) == 7
        for pid in sm:
            assert sm[pid]["sdf_vector"] == rm[pid]["sdf_vector"]
            assert sm[pid]["vector_sum"] == rm[pid]["vector_sum"]
