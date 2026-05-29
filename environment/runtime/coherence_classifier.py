"""
Coherence classifier for EEG brainwave analysis.

Analyzes final spectral vectors to classify electrode channel relationships
and determine processing priority for BCI feature extraction.
"""


def vector_leq(a, b):
    """Check if vector a is component-wise <= vector b."""
    return all(x <= y for x, y in zip(a, b))


def vector_dominates(a, b):
    """Check if vector a strictly dominates b (a >= b with at least one a > b)."""
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def channels_are_decoupled(vec_a, vec_b):
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
    return a_within_b and b_within_a


def compute_extraction_priority(channels, vectors, events):
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
    return sorted(channels, key=lambda ch: last_event_seq.get(ch, 0))


def classify_all_pairs(channels, vectors):
    """Classify all channel pairs as decoupled or entangled.

    Returns dict with:
        - decoupled_pairs: list of (ch1, ch2) tuples
        - entangled_pairs: list of (ch1, ch2) tuples
        - decoupled_count: number of decoupled pairs
    """
    decoupled = []
    entangled = []

    for i in range(len(channels)):
        for j in range(i + 1, len(channels)):
            vec_i = vectors[channels[i]]
            vec_j = vectors[channels[j]]
            if channels_are_decoupled(vec_i, vec_j):
                decoupled.append((channels[i], channels[j]))
            else:
                entangled.append((channels[i], channels[j]))

    return {
        "decoupled_pairs": decoupled,
        "entangled_pairs": entangled,
        "decoupled_count": len(decoupled),
    }


def analyze_coherence(channels, vectors, events):
    """Full coherence analysis producing classification and priority.

    Returns dict with pair classification and extraction priority.
    """
    pair_data = classify_all_pairs(channels, vectors)
    priority = compute_extraction_priority(channels, vectors, events)

    return {
        "pair_classification": pair_data,
        "extraction_priority": priority,
    }
