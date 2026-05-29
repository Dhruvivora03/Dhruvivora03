# EEG Brainwave Coherence Analysis — Debugging Task

## Overview

A brain-computer interface (BCI) pipeline processes EEG recordings from 7 electrode channels placed according to the international 10-20 system. The system tracks accumulated spectral power through alpha pulses, gamma spikes, and phase-entrainment events, then classifies inter-channel coherence relationships and computes feature extraction priority for the BCI decoder.

The pipeline is producing incorrect results. Several output values do not match expected values from validated calibration runs.

## Observed Symptoms

1. **Spectral power too low**: Electrode fp1 should report own power of **15** after all events, but the pipeline reports **14**. Similarly, electrode fp2 reports 11 instead of 12, c3 reports 8 instead of 9, and c4 reports 10 instead of 11.

2. **No decoupled pairs detected**: The coherence report shows 0 decoupled channel pairs, but the expected count is **21** (all pairs should be spectrally decoupled given the electrode placement geometry).

3. **Wrong extraction priority**: The priority list starts with `electrode_c3` and ends with `electrode_fp2`, but correct ordering should start with a low-power channel (`electrode_o1`) and end with a high-power channel (`electrode_fp1`).

4. **Digest mismatch**: Expected digest is `a2fe66602a4fc2e1`, pipeline produces `fe6d0cb4534ff40a`.

## File Layout

All runtime files are located at `/app/runtime/`:

```
/app/runtime/
├── data/
│   └── eeg_recording.dat         — Electrode recording (input data)
├── signal_decoder.py             — Decodes recording into events
├── spectral_accumulator.py       — Builds spectral vectors per channel
├── coherence_classifier.py       — Classifies pairs and computes priority
├── bci_report.py                 — Generates final JSON report
└── run_bci.py                    — Orchestrates the pipeline
```

## Files Known to Be Correct

- `/app/runtime/signal_decoder.py` — Decoding logic is verified correct
- `/app/runtime/run_bci.py` — Orchestration logic is verified correct
- `/app/runtime/data/eeg_recording.dat` — Input data is verified correct

## Files Containing Bugs

- `/app/runtime/spectral_accumulator.py` — Spectral tracking has an error
- `/app/runtime/coherence_classifier.py` — Coherence analysis has errors
- `/app/runtime/bci_report.py` — Report generation inherits analysis errors

## Output Schema

### bci_state.jsonl

One JSON record per line. Channel state records:
```json
{"type": "channel_state", "channel_id": "electrode_fp1", "spectral_vector": [...], "own_power": 15}
```

Event summary record:
```json
{"type": "event_summary", "total_events": 45, "per_channel": {"electrode_fp1": 9, ...}}
```

### coherence_report.json

```json
{
  "session_summary": {"channel_count": 7, "total_events": 45, "channels": [...]},
  "spectral_state": {"electrode_fp1": {"vector": [...], "vector_sum": 51}, ...},
  "pair_classification": {"decoupled_pairs": [...], "entangled_pairs": [...], "decoupled_count": 21, "total_pairs": 21},
  "extraction_priority": ["electrode_o1", "electrode_o2", "electrode_p3", ...],
  "validation": {"digest": "a2fe66602a4fc2e1"}
}
```

## Signal Types

- **PULSE**: Alpha-band oscillation, adds +1 to channel's own spectral power
- **SPIKE**: Gamma-band burst, adds +2 to channel's own spectral power
- **ENTRAIN**: Phase coupling with neighboring channel, propagates spectral knowledge

## Constraints

- All channels start with BASE_POWER = 3
- There are 7 electrode channels with 45 total recording events
- Channels that entrain: fp1, fp2, c3, c4 (1 entrainment each)
- Channels that never entrain: o1, o2, p3
