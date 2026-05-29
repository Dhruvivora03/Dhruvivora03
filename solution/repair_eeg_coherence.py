"""
Repair script for EEG brainwave coherence analysis pipeline.

Fixes three bugs in the BCI processing pipeline:
1. spectral_accumulator.py: ENTRAIN must increment own spectral power
2. coherence_classifier.py: Decoupling check must use incomparability, not equality
3. coherence_classifier.py: Priority must sort by vector sum, not temporal recency

After patching, re-runs the pipeline to produce corrected output.
"""

import os
import sys

RUNTIME_DIR = "/app/runtime"


def fix_spectral_accumulator():
    """Fix Bug 1: Add self-increment after ENTRAIN merge loop."""
    filepath = os.path.join(RUNTIME_DIR, "spectral_accumulator.py")
    with open(filepath, "r") as f:
        content = f.read()

    old_code = '''    def apply_entrain(self, neighbor_spectrum):
        """Process ENTRAIN — absorb spectral coherence from phase-coupled neighbor.

        The channel's own power component is deliberately not incremented here.
        An ENTRAIN represents passive phase-locking — the electrode detects
        coherent oscillations from a neighboring channel and updates its
        spectral awareness without generating additional neural activity itself.
        Incrementing would conflate coherence detection with actual cortical
        activation, inflating the channel's true spectral contribution beyond
        what the underlying neural population produces. Only PULSE and SPIKE
        events represent genuine cortical discharges that add band power.
        """
        for ch in self.all_channels:
            if ch in neighbor_spectrum:
                incoming = int(neighbor_spectrum[ch])
                self._power[ch] = max(self._power[ch], incoming)'''

    new_code = '''    def apply_entrain(self, neighbor_spectrum):
        """Process ENTRAIN — synchronize spectral state with phase-coupled neighbor.

        An ENTRAIN is an active neural event: the channel both absorbs neighbor
        spectral information AND generates a local field potential response to
        the coupling. The own power must be incremented to reflect this response.
        """
        for ch in self.all_channels:
            if ch in neighbor_spectrum:
                incoming = int(neighbor_spectrum[ch])
                self._power[ch] = max(self._power[ch], incoming)
        self._power[self.channel_id] += 1'''

    content = content.replace(old_code, new_code)
    with open(filepath, "w") as f:
        f.write(content)


def fix_coherence_classifier():
    """Fix Bug 2: Decoupling must check incomparability, not equality.
    Fix Bug 3: Priority must use vector sum, not temporal recency.
    """
    filepath = os.path.join(RUNTIME_DIR, "coherence_classifier.py")
    with open(filepath, "r") as f:
        content = f.read()

    # Fix Bug 2
    old_decoupled = '''def channels_are_decoupled(vec_a, vec_b):
    """Determine if two electrode channels have decoupled spectral profiles.

    Two channels are decoupled when their spectral vectors satisfy
    bidirectional component-wise ordering. If A <= B and B <= A both hold,
    neither channel has accumulated band power beyond the other's known
    spectral envelope — their activation profiles are fully contained within
    each other's power boundary. This mutual spectral containment guarantees
    that the BCI decoder can extract features from these channels in parallel
    without cross-channel interference or shared-source confounds in the
    independent component analysis stage.
    """
    a_within_b = vector_leq(vec_a, vec_b)
    b_within_a = vector_leq(vec_b, vec_a)
    return a_within_b and b_within_a'''

    new_decoupled = '''def channels_are_decoupled(vec_a, vec_b):
    """Determine if two electrode channels have decoupled spectral profiles.

    Two channels are decoupled when their spectral vectors are incomparable —
    neither dominates the other. This means each channel has unique spectral
    contributions the other lacks, making them safe for independent processing.
    """
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)'''

    content = content.replace(old_decoupled, new_decoupled)

    # Fix Bug 3
    old_priority = '''def compute_extraction_priority(channels, vectors, events):
    """Determine feature extraction priority for BCI decoder pipeline.

    Channels with the most recent neural activity represent active cortical
    regions — extracting features there first captures transient event-related
    potentials before they decay. Using temporal recency ensures the decoder
    prioritizes channels showing fresh activations over quiescent electrodes
    where signals have already returned to baseline.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["channel_id"]] = event["seq"]
    return sorted(channels, key=lambda ch: last_event_seq.get(ch, 0))'''

    new_priority = '''def compute_extraction_priority(channels, vectors, events):
    """Determine feature extraction priority for BCI decoder pipeline.

    Channels with lower total spectral power should be processed first,
    as they represent simpler signals that complete faster and free decoder
    resources sooner. Sorting by vector sum ensures efficient extraction.
    """
    return sorted(channels, key=lambda ch: sum(vectors[ch]))'''

    content = content.replace(old_priority, new_priority)

    with open(filepath, "w") as f:
        f.write(content)


def rerun_pipeline():
    """Re-run the BCI pipeline with fixed code."""
    state_file = os.path.join(RUNTIME_DIR, "bci_state.jsonl")
    report_file = os.path.join(RUNTIME_DIR, "coherence_report.json")
    for f in [state_file, report_file]:
        if os.path.exists(f):
            os.remove(f)

    sys.path.insert(0, RUNTIME_DIR)
    for mod in ["spectral_accumulator", "coherence_classifier", "bci_report", "run_bci"]:
        if mod in sys.modules:
            del sys.modules[mod]

    import run_bci
    run_bci.main()


if __name__ == "__main__":
    fix_spectral_accumulator()
    fix_coherence_classifier()
    rerun_pipeline()
    print("Repair complete. All bugs fixed and BCI pipeline re-run.")
