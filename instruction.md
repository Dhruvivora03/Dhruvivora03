# Event Store Replay Repair — Debugging Task

## Overview

An event sourcing replay engine ingests domain events from multiple aggregate streams, orders them deterministically, rebuilds materialized projections through sequential event application, and replays events in configurable epochs. The system produces replay logs and projection statistics as JSON output.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Stream Loading** — Reads CSV event files (orders, payments, inventory) based on the active aggregates configuration. Each aggregate stream provides domain events with payload values, version numbers, timestamps, and per-aggregate sequence numbers.

2. **Event Ordering** — Sorts all loaded events into a single deterministic sequence for replay. Events are ordered by `(timestamp, aggregate_id, seq_number)` to ensure stable ordering even when events from different aggregates share the same timestamp.

3. **Projection Building** — Applies events to materialized projections using the `[projection.materialized]` configuration section for the snapshot interval. Computes per-aggregate state including payload totals and version-weighted projection scores.

4. **Epoch Replay** — Processes the ordered events in configurable epoch sizes and tracks replay progress. Epoch statistics represent the per-aggregate event counts from the last processing epoch only.

5. **Output Generation** — Writes the replay log and projection statistics to JSON files in the output directory.

## Problem

The engine runs without errors but produces incorrect results:

- Some aggregate events appear to be missing from the replay entirely
- Projection scores are deflated because the snapshot interval is too large
- Epoch processing statistics report inflated counts that exceed actual per-epoch event numbers
- Event ordering shows non-deterministic behavior for events with equal timestamps

## Expected Correct Output

When all defects are fixed:

- All 55 events (20 orders + 18 payments + 17 inventory) should be loaded and replayed
- The snapshot interval should be 5 (from `[projection.materialized]` section)
- Epoch processing statistics should report per-aggregate counts from the final epoch only: orders=1, payments=2 (inventory does not appear in the final epoch)
- Event ordering should be deterministically sorted by `(timestamp, aggregate_id, seq_number)`

## Output Schema

### `/app/runtime/output/replay_log.json`

| Field | Type | Description |
|-------|------|-------------|
| `replay_log` | list | List of replayed event entries |
| `replay_log[].event_id` | string | Event identifier |
| `replay_log[].aggregate_id` | string | Source aggregate stream name |
| `replay_log[].seq_number` | integer | Per-aggregate sequence number |
| `replay_log[].event_type` | string | Domain event type name |
| `replay_log[].payload_value` | integer | Event payload value |
| `replay_log[].timestamp` | integer | Event timestamp |
| `replay_log[].replayed` | boolean | Whether the event was successfully replayed |
| `replay_log[].epoch_index` | integer | Processing epoch number |
| `ordered_events_head` | list | First 10 events in replay order |
| `ordered_events_head[].event_id` | string | Event identifier |
| `ordered_events_head[].aggregate_id` | string | Source aggregate stream name |
| `ordered_events_head[].event_type` | string | Domain event type name |
| `ordered_events_head[].timestamp` | integer | Event timestamp |
| `total_events_loaded` | integer | Total number of events in the replay |

### `/app/runtime/output/projection_stats.json`

| Field | Type | Description |
|-------|------|-------------|
| `projection_statistics` | object | Projection metrics |
| `projection_statistics.total_projected` | integer | Total events projected |
| `projection_statistics.snapshot_interval` | integer | Active snapshot interval |
| `projection_statistics.aggregate_count` | integer | Number of distinct aggregates |
| `replay_summary` | object | Replay execution metrics |
| `replay_summary.total_events` | integer | Total events in replay log |
| `replay_summary.replayed_count` | integer | Events successfully replayed |
| `replay_summary.failed_count` | integer | Events that failed replay |
| `replay_summary.aggregate_count` | integer | Number of distinct aggregates |
| `replay_summary.epoch_count` | integer | Total number of processing epochs |
| `epoch_processing_stats` | object | Per-aggregate event counts from final epoch |
| `epoch_processing_stats.<aggregate>` | integer | Event count for that aggregate in the final epoch |
| `projections` | object | Per-aggregate materialized projection state |
| `projections.<aggregate>.aggregate_id` | string | Aggregate identifier |
| `projections.<aggregate>.total_payload` | integer | Cumulative payload total |
| `projections.<aggregate>.event_count` | integer | Number of events projected |
| `projections.<aggregate>.last_version` | integer | Most recent event version |
| `projections.<aggregate>.last_event_type` | string | Most recent event type |
| `projections.<aggregate>.projection_score` | float | Version-weighted projection score |
| `engine_config` | object | Runtime configuration parameters |
| `engine_config.epoch_size` | integer | Epoch processing batch size |
| `engine_config.snapshot_interval` | integer | Active snapshot interval |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Configuration with aggregate list, projection parameters, and replay settings |
| `/app/runtime/stream_loader.py` | Loads and filters event records from CSV aggregate stream files |
| `/app/runtime/event_ordering.py` | Deterministic event ordering across multiple aggregate streams |
| `/app/runtime/event_projector.py` | Builds materialized projections with version-weighted scoring |
| `/app/runtime/replay_engine.py` | Epoch-based event replay with per-epoch statistics tracking |
| `/app/runtime/run_replay.py` | Main entry point orchestrating the full process |
| `/app/runtime/data/orders_events.csv` | Order aggregate events (20 entries) |
| `/app/runtime/data/payments_events.csv` | Payment aggregate events (18 entries) |
| `/app/runtime/data/inventory_events.csv` | Inventory aggregate events (17 entries) |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The data files are correct — the bugs are in the Python source code and its interaction with the configuration file. Focus on:

- How aggregate names are parsed from the configuration
- Which configuration section provides projection parameters
- How epoch processing statistics are aggregated across epochs
- How event ordering handles timestamp ties in sorting
