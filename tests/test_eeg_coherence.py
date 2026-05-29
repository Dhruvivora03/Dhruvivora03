"""
Test suite for EEG brainwave coherence analysis pipeline.

Validates BCI processing correctness across four tiers:
  Tier 1 (6 tests): Structural validation — output existence and format
  Tier 2 (3 tests): Spectral state values — per-channel vector correctness
  Tier 3 (3 tests): Coherence classification — channel decoupling and priority
  Tier 4 (2 tests): Full consistency — digest and cross-validation
"""

import json
import os
import sys

sys.path.insert(0, "/app/runtime")

STATE_FILE = "/app/runtime/bci_state.jsonl"
REPORT_FILE = "/app/runtime/coherence_report.json"

EXPECTED_CHANNELS = [
    "electrode_c3",
    "electrode_c4",
    "electrode_fp1",
    "electrode_fp2",
    "electrode_o1",
    "electrode_o2",
    "electrode_p3",
]

TOTAL_EVENTS = 45
EVENTS_PER_CHANNEL = {
    "electrode_fp1": 9,
    "electrode_fp2": 7,
    "electrode_c3": 5,
    "electrode_c4": 6,
    "electrode_p3": 6,
    "electrode_o1": 6,
    "electrode_o2": 6,
}


def load_state():
    """Load BCI state from JSONL file."""
    records = []
    with open(STATE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_report():
    """Load coherence report from JSON file."""
    with open(REPORT_FILE, "r") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════
# TIER 1: Structural validation (always pass with buggy code)
# ═══════════════════════════════════════════════════════════════


class TestTier1Structural:
    """Structural tests that validate output format and existence."""

    def test_output_files_exist(self):
        """Both state and report files must be generated."""
        assert os.path.isfile(STATE_FILE), f"State file missing: {STATE_FILE}"
        assert os.path.isfile(REPORT_FILE), f"Report file missing: {REPORT_FILE}"

    def test_channel_count(self):
        """BCI must process exactly 7 electrode channels."""
        report = load_report()
        assert report["session_summary"]["channel_count"] == 7

    def test_channel_ids(self):
        """All expected channel IDs must be present in report."""
        report = load_report()
        channels = sorted(report["session_summary"]["channels"])
        assert channels == EXPECTED_CHANNELS

    def test_events_per_channel(self):
        """Event distribution must match recording file."""
        state = load_state()
        summary = None
        for record in state:
            if record["type"] == "event_summary":
                summary = record
                break
        assert summary is not None, "No event_summary record in state file"
        for cid, expected_count in EVENTS_PER_CHANNEL.items():
            actual = summary["per_channel"].get(cid, 0)
            assert actual == expected_count, (
                f"{cid}: expected {expected_count} events, got {actual}"
            )

    def test_required_fields(self):
        """Each channel state record must have required fields."""
        state = load_state()
        channel_records = [r for r in state if r["type"] == "channel_state"]
        for record in channel_records:
            assert "channel_id" in record
            assert "spectral_vector" in record
            assert "own_power" in record
            assert len(record["spectral_vector"]) == 7

    def test_total_event_count(self):
        """Total event count must equal 45."""
        state = load_state()
        summary = None
        for record in state:
            if record["type"] == "event_summary":
                summary = record
                break
        assert summary is not None
        assert summary["total_events"] == TOTAL_EVENTS


# ═══════════════════════════════════════════════════════════════
# TIER 2: Spectral state values (need Bug 1 fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier2SpectralState:
    """Tests that validate spectral vector correctness after ENTRAIN."""

    def test_power_after_entrain(self):
        """Electrode fp1's own power must be 15 after ENTRAIN + subsequent events.

        fp1 has 9 events: PULSE(+1) + SPIKE(+2) + PULSE(+1) + ENTRAIN(+1) +
        PULSE(+1) + SPIKE(+2) + PULSE(+1) + PULSE(+1) + SPIKE(+2) = BASE(3) + 12 = 15.
        If ENTRAIN does not increment, own power is only 14.
        """
        state = load_state()
        for record in state:
            if record["type"] == "channel_state" and record["channel_id"] == "electrode_fp1":
                assert record["own_power"] == 15, (
                    f"electrode_fp1 own_power: expected 15, got {record['own_power']}. "
                    f"ENTRAIN events must increment the channel's own spectral power."
                )
                return
        assert False, "electrode_fp1 state record not found"

    def test_entrain_spectral_absorption(self):
        """Electrode fp2 must absorb fp1's spectral data during ENTRAIN.

        fp2 entrains with peer_state showing fp1 at 7. fp2's vector at
        fp1's position (index 2) should be max(BASE, 7) = 7.
        """
        state = load_state()
        for record in state:
            if record["type"] == "channel_state" and record["channel_id"] == "electrode_fp2":
                # fp2's vector at fp1's index (index 2) should be 7
                assert record["spectral_vector"][2] == 7, (
                    f"electrode_fp2 vector[2]: expected 7 (absorbed from fp1 via ENTRAIN), "
                    f"got {record['spectral_vector'][2]}"
                )
                return
        assert False, "electrode_fp2 state record not found"

    def test_vector_sums_with_entrain(self):
        """Channels with ENTRAIN events must have correct vector sums.

        Entrained channels (fp1, fp2, c3, c4) accumulate extra power from
        the entrainment event itself. Non-entrained channels (o1, o2, p3)
        have sum=29.
        """
        report = load_report()
        ss = report["spectral_state"]

        # Non-entrained channels have sum=29
        for cid in ["electrode_o1", "electrode_o2", "electrode_p3"]:
            assert ss[cid]["vector_sum"] == 29, (
                f"{cid} vector_sum: expected 29, got {ss[cid]['vector_sum']}"
            )

        # Entrained channels: correct sums include ENTRAIN self-increment
        entrained_expected = {
            "electrode_fp1": 51,
            "electrode_fp2": 49,
            "electrode_c3": 47,
            "electrode_c4": 51,
        }
        for cid, expected_sum in entrained_expected.items():
            assert ss[cid]["vector_sum"] == expected_sum, (
                f"{cid} vector_sum: expected {expected_sum}, got {ss[cid]['vector_sum']}"
            )


# ═══════════════════════════════════════════════════════════════
# TIER 3: Coherence classification (need Bugs 2+3 fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier3CoherenceClassification:
    """Tests that validate channel decoupling and priority ordering."""

    def test_priority_not_temporal(self):
        """Extraction priority must NOT be based on temporal recency.

        Correct priority sorts by total spectral power (vector sum).
        First channel must be one of the lowest-sum electrodes (o1/o2/p3, sum=29).
        Last channel must be one of the highest-sum electrodes (fp1/c4, sum=51).
        """
        report = load_report()
        priority = report["extraction_priority"]

        low_sum_channels = {"electrode_o1", "electrode_o2", "electrode_p3"}
        high_sum_channels = {"electrode_fp1", "electrode_c4"}

        assert priority[0] in low_sum_channels, (
            f"First in priority should be a low-sum channel (o1/o2/p3), "
            f"got {priority[0]}"
        )
        assert priority[-1] in high_sum_channels, (
            f"Last in priority should be a high-sum channel (fp1/c4), "
            f"got {priority[-1]}"
        )

    def test_decoupled_pair_count(self):
        """Exactly 21 channel pairs must be classified as decoupled.

        With correct spectral vectors, no channel's vector dominates another's
        (each channel has its own component as the unique maximum). All 21
        pairs of 7 channels are spectrally decoupled.
        """
        report = load_report()
        pair_data = report["pair_classification"]
        assert pair_data["decoupled_count"] == 21, (
            f"Decoupled pair count: expected 21, got {pair_data['decoupled_count']}. "
            f"Decoupling means neither vector dominates the other."
        )

    def test_classification_no_entangled(self):
        """All 21 pairs must be decoupled with zero entangled pairs."""
        report = load_report()
        pair_data = report["pair_classification"]
        total = pair_data["decoupled_count"] + len(pair_data["entangled_pairs"])
        expected_total = 21  # C(7,2) = 21
        assert total == expected_total, (
            f"Total classified pairs: expected {expected_total}, got {total}"
        )
        assert len(pair_data["entangled_pairs"]) == 0, (
            f"Expected 0 entangled pairs, got {len(pair_data['entangled_pairs'])}. "
            f"No channel's vector should dominate another's."
        )


# ═══════════════════════════════════════════════════════════════
# TIER 4: Full consistency (need ALL bugs fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier4Consistency:
    """Tests that validate end-to-end pipeline consistency."""

    def test_digest_fingerprint(self):
        """Report digest must match expected value for correct analysis.

        The 16-character hex digest validates that spectral vectors, pair
        classifications, and priority ordering are all correct simultaneously.
        """
        report = load_report()
        expected_digest = "a2fe66602a4fc2e1"
        actual_digest = report["validation"]["digest"]
        assert actual_digest == expected_digest, (
            f"Digest mismatch: expected {expected_digest}, got {actual_digest}. "
            f"This indicates one or more pipeline stages produce incorrect results."
        )

    def test_state_report_cross_validation(self):
        """State file vectors must match report spectral state exactly."""
        state = load_state()
        report = load_report()

        state_vectors = {}
        for record in state:
            if record["type"] == "channel_state":
                state_vectors[record["channel_id"]] = record["spectral_vector"]

        for cid in EXPECTED_CHANNELS:
            assert cid in state_vectors, f"{cid} missing from state file"
            assert cid in report["spectral_state"], f"{cid} missing from report"
            state_vec = state_vectors[cid]
            report_vec = report["spectral_state"][cid]["vector"]
            assert state_vec == report_vec, (
                f"{cid} vector mismatch between state and report: "
                f"state={state_vec}, report={report_vec}"
            )
