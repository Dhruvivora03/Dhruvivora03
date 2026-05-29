# Audio Forensics Fingerprint Analysis — Debugging Task

## Overview

An audio forensics pipeline analyzes 7 audio tracks to detect near-duplicate content through spectral fingerprinting. The system loads pre-computed spectral coefficients, applies sliding-window fingerprinting to produce compact feature vectors, computes pairwise similarity between all tracks, and performs hierarchical clustering to identify duplicate groups.

The pipeline is producing incorrect results. Several output values do not match expected values from validated reference runs.

## Observed Symptoms

1. **Too few fingerprint segments**: Each track should produce **3** fingerprint segments from 8 spectral frames, but the pipeline produces only **2**. The composite fingerprint for track_alpha has last coefficient ~1.2000 instead of expected ~1.1917.

2. **Similarity scores out of range**: The top similarity score between any track pair is reported as ~29.3 which is outside the valid [0, 1] range. Expected top similarity (track_delta vs track_zeta) should be ~0.9999.

3. **Wrong cluster count**: Only **1** duplicate group is reported (containing all 7 tracks), but the expected result is **2** distinct duplicate groups: {track_alpha, track_gamma} and {track_delta, track_zeta}. Three tracks (beta, epsilon, eta) should be classified as singletons.

4. **Digest mismatch**: Expected digest is `312e1292f1643efd`, pipeline produces `960961fb9c30e647`.

## File Layout

All runtime files are located at `/app/runtime/`:

```
/app/runtime/
├── data/
│   └── spectral_coefficients.dat  — Pre-computed STFT coefficients (input)
├── spectrum_loader.py             — Loads spectral data from file
├── fingerprint_engine.py          — Sliding-window fingerprint computation
├── similarity_matrix.py           — Pairwise similarity scoring
├── cluster_builder.py             — Hierarchical agglomerative clustering
├── forensics_report.py            — Generates final JSON report
└── run_forensics.py               — Orchestrates the pipeline
```

## Files Known to Be Correct

- `/app/runtime/spectrum_loader.py` — Data loading is verified correct
- `/app/runtime/run_forensics.py` — Orchestration logic is verified correct
- `/app/runtime/data/spectral_coefficients.dat` — Input data is verified correct

## Files Containing Bugs

- `/app/runtime/fingerprint_engine.py` — Window stride computation has an error
- `/app/runtime/similarity_matrix.py` — Similarity scoring has an error
- `/app/runtime/cluster_builder.py` — Linkage criterion has an error
- `/app/runtime/forensics_report.py` — Report generation inherits scoring errors

## Output Schema

### forensics_state.jsonl

One JSON record per line. Track fingerprint records:
```json
{"type": "track_fingerprint", "track_id": "track_alpha", "segment_count": 3, "composite": [...], "frame_count": 8}
```

Analysis summary record:
```json
{"type": "analysis_summary", "total_tracks": 7, "frames_per_track": 8, "coefficients_per_frame": 6}
```

### dedup_report.json

```json
{
  "analysis_summary": {"track_count": 7, "tracks": [...]},
  "fingerprints": {"track_alpha": {"segment_count": 3, "composite": [...]}, ...},
  "similarity": {"top_pairs": [["track_delta", "track_zeta", 0.999946], ...], "threshold": 0.92},
  "clustering": {
    "clusters": [["track_delta", "track_zeta"], ["track_alpha", "track_gamma"], ...],
    "duplicate_groups": [["track_alpha", "track_gamma"], ["track_delta", "track_zeta"]],
    "duplicate_group_count": 2,
    "singleton_tracks": ["track_beta", "track_epsilon", "track_eta"]
  },
  "validation": {"digest": "312e1292f1643efd"}
}
```

## Pipeline Parameters

- **Window size**: 4 frames
- **Coefficients per frame**: 6
- **Frames per track**: 8
- **Similarity threshold**: 0.92 (minimum for duplicate consideration)
- **Tracks analyzed**: 7

## Expected Duplicate Relationships

- track_alpha ≈ track_gamma (near-identical spectral profiles)
- track_delta ≈ track_zeta (near-identical spectral profiles)
- track_beta, track_epsilon, track_eta are unique (no matches above threshold)
