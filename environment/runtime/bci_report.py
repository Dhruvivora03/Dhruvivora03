"""
BCI report writer for EEG brainwave coherence analysis.

Generates the final coherence report in JSON format, including per-channel
spectral summaries, decoupling classifications, and a consistency digest
for validation of the full BCI processing pipeline.
"""

import json
import hashlib
from coherence_classifier import channels_are_decoupled, compute_extraction_priority


def compute_digest(channels, vectors, decoupled_pairs, priority_order):
    """Compute 16-char hex digest of BCI results for validation.

    Combines channel vectors, pair classifications, and priority ordering
    into a single fingerprint that validates end-to-end correctness.
    """
    h = hashlib.sha256()

    # Include all vectors in sorted channel order
    for ch in sorted(channels):
        vec_str = ",".join(str(v) for v in vectors[ch])
        h.update(f"{ch}:{vec_str}\n".encode())

    # Include decoupled pairs
    for ch1, ch2 in sorted(decoupled_pairs):
        h.update(f"decoupled:{ch1},{ch2}\n".encode())

    # Include priority order
    h.update(f"priority:{','.join(priority_order)}\n".encode())

    return h.hexdigest()[:16]


def generate_report(channels, vectors, events, output_path):
    """Generate full BCI coherence report as JSON.

    Performs pair classification using channel decoupling check,
    computes extraction priority, and writes comprehensive report.
    """
    # Classify all pairs
    decoupled_pairs = []
    entangled_pairs = []

    for i in range(len(channels)):
        for j in range(i + 1, len(channels)):
            vec_i = vectors[channels[i]]
            vec_j = vectors[channels[j]]
            if channels_are_decoupled(vec_i, vec_j):
                decoupled_pairs.append((channels[i], channels[j]))
            else:
                entangled_pairs.append((channels[i], channels[j]))

    # Compute priority
    priority_order = compute_extraction_priority(channels, vectors, events)

    # Compute digest
    digest = compute_digest(channels, vectors, decoupled_pairs, priority_order)

    # Build report
    report = {
        "session_summary": {
            "channel_count": len(channels),
            "total_events": len(events),
            "channels": sorted(channels),
        },
        "spectral_state": {},
        "pair_classification": {
            "decoupled_pairs": [list(p) for p in decoupled_pairs],
            "entangled_pairs": [list(p) for p in entangled_pairs],
            "decoupled_count": len(decoupled_pairs),
            "total_pairs": len(decoupled_pairs) + len(entangled_pairs),
        },
        "extraction_priority": priority_order,
        "validation": {
            "digest": digest,
        },
    }

    # Add per-channel state
    for ch in sorted(channels):
        report["spectral_state"][ch] = {
            "vector": vectors[ch],
            "vector_sum": sum(vectors[ch]),
        }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report
