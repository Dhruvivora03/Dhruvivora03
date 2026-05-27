# Task Scheduler Repair — Debugging Task

## Overview

A deadline-based task scheduling engine ingests job definitions from multiple stream sources, constructs a priority queue using urgency-weighted scoring, and resolves inter-job dependencies in iterative processing waves. The system produces execution plans and queue statistics as JSON output.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Stream Loading** — Reads CSV job files (compute, io, network) based on the active streams configuration. Each stream provides job records with deadlines, costs, dependencies, timestamps, and per-stream insertion sequence numbers.

2. **Priority Queue Construction** — Builds a deadline-based priority queue from the loaded jobs. The queue uses scheduling-specific parameters from the `[scheduling.deadline]` configuration section for the urgency multiplier that weights deadline proximity in score computation.

3. **Execution Ordering** — Jobs are sorted in descending priority order for execution. Ties in priority score are broken deterministically by `(stream_id, seq_number)` to produce stable execution ordering across runs.

4. **Dependency Resolution** — Processes the ordered jobs in configurable wave sizes and tracks which jobs have their dependencies satisfied. Wave statistics represent the per-stream job counts from the last processing wave only.

5. **Output Generation** — Writes the execution plan and queue statistics to JSON files in the output directory.

## Problem

The engine runs without errors but produces incorrect results:

- Some stream jobs appear to be missing from the queue entirely
- Priority scores seem deflated compared to expected values
- Wave processing statistics report inflated counts that exceed actual per-wave job numbers
- Execution ordering shows non-deterministic behavior for jobs with equal priority scores

## Expected Correct Output

When all defects are fixed:

- All 55 jobs (20 compute + 18 io + 17 network) should be enqueued
- The urgency multiplier should be 2.5 (from `[scheduling.deadline]` section)
- Wave processing statistics should report per-stream counts from the final wave only: compute=1, io=2, network=1
- Execution ordering should be deterministically sorted by (-priority_score, stream_id, seq_number)

## Output Schema

### `/app/runtime/output/execution_plan.json`

| Field | Type | Description |
|-------|------|-------------|
| `execution_plan` | list | List of resolved job execution entries |
| `execution_plan[].id` | string | Job identifier |
| `execution_plan[].stream_id` | string | Source stream name |
| `execution_plan[].seq_number` | integer | Per-stream sequence number |
| `execution_plan[].label` | string | Job label |
| `execution_plan[].priority_score` | float | Computed deadline-based priority score |
| `execution_plan[].depends_on` | string or null | Dependency job ID |
| `execution_plan[].resolved` | boolean | Whether dependencies are satisfied |
| `execution_plan[].wave_index` | integer | Processing wave number |
| `top_priority_jobs` | list | Top-10 highest priority jobs |
| `top_priority_jobs[].id` | string | Job identifier |
| `top_priority_jobs[].stream_id` | string | Source stream name |
| `top_priority_jobs[].label` | string | Job label |
| `top_priority_jobs[].priority_score` | float | Priority score |
| `total_jobs_loaded` | integer | Total number of jobs in the queue |

### `/app/runtime/output/queue_stats.json`

| Field | Type | Description |
|-------|------|-------------|
| `queue_statistics` | object | Priority queue metrics |
| `queue_statistics.total_enqueued` | integer | Total jobs enqueued |
| `queue_statistics.urgency_multiplier` | float | Active urgency multiplier |
| `queue_statistics.max_deadline` | integer | Maximum deadline value |
| `queue_statistics.score_range` | object | Min and max priority scores |
| `queue_statistics.score_range.min` | float | Minimum priority score |
| `queue_statistics.score_range.max` | float | Maximum priority score |
| `resolution_summary` | object | Dependency resolution metrics |
| `resolution_summary.total_jobs` | integer | Total jobs in plan |
| `resolution_summary.resolved_count` | integer | Jobs with satisfied dependencies |
| `resolution_summary.unresolved_count` | integer | Jobs with unsatisfied dependencies |
| `resolution_summary.stream_count` | integer | Number of distinct streams |
| `resolution_summary.wave_count` | integer | Total number of processing waves |
| `wave_processing_stats` | object | Per-stream job counts from final wave |
| `wave_processing_stats.compute` | integer | Compute jobs in final wave |
| `wave_processing_stats.io` | integer | IO jobs in final wave |
| `wave_processing_stats.network` | integer | Network jobs in final wave |
| `execution_config` | object | Runtime configuration parameters |
| `execution_config.wave_size` | integer | Wave processing batch size |
| `execution_config.urgency_multiplier` | float | Active urgency multiplier |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Configuration with stream list, scheduling parameters, and execution settings |
| `/app/runtime/stream_loader.py` | Loads and filters job records from CSV stream files |
| `/app/runtime/priority_queue.py` | Priority queue with deadline-based scoring and execution ordering |
| `/app/runtime/dependency_resolver.py` | Resolves job dependencies in iterative waves and computes statistics |
| `/app/runtime/run_scheduler.py` | Main entry point orchestrating the full process |
| `/app/runtime/data/compute_jobs.csv` | Compute job records (20 entries) |
| `/app/runtime/data/io_jobs.csv` | IO job records (18 entries) |
| `/app/runtime/data/network_jobs.csv` | Network job records (17 entries) |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The data files are correct — the bugs are in the Python source code and its interaction with the configuration file. Focus on:

- How stream names are parsed from the configuration
- Which configuration section provides scheduling parameters
- How wave processing statistics are aggregated across waves
- How execution ordering handles priority score ties in sorting
