# Scheduler Repair — Debugging Task

## Overview

A task scheduler engine reads job definitions from multiple category sources (compute, IO, maintenance), resolves inter-job dependencies using topological ordering, schedules execution based on priority with deterministic tiebreaking, and produces resource utilization reports across configurable processing epochs.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Job Loading** — Reads CSV job files from each configured active category. Each category provides job definitions with priorities, durations, dependency lists, and per-category sequence numbers.

2. **Dependency Resolution** — Resolves execution order using topological sort. Jobs with no unmet dependencies are scheduled first. Among ready jobs, ordering uses `(-priority, category_id, seq)` to ensure deterministic tiebreaking when multiple jobs share the same priority.

3. **Metrics Computation** — Calculates total duration, critical path depth through the dependency graph, and per-category job counts from the resolved execution order.

4. **Epoch Resources** — Computes per-category resource utilization within processing epochs. The engine uses parallel scheduling parameters from the `[scheduling.parallel]` configuration section. The final resource report represents utilization from the last processing epoch only.

5. **Output Generation** — Writes the execution plan and resource report to JSON files in the output directory.

## Problem

The engine runs without errors but produces incorrect results:

- Some job categories appear to be missing from the schedule entirely
- Processing epochs are larger than expected, reducing granularity of resource tracking
- Resource utilization values appear inflated beyond what the actual jobs would produce
- Job ordering shows inconsistencies for jobs sharing the same priority level

## Expected Correct Output

When all defects are fixed:

- All 55 jobs (20 compute + 18 io + 17 maintenance) should be scheduled
- Processing epochs should use a size of 10 jobs (from parallel configuration)
- Epoch resources should report per-category durations from the final epoch only: compute=905, io=355, maintenance=135
- Jobs with equal priority should be ordered deterministically by (-priority, category_id, seq)

## Output Schema

### `/app/runtime/output/schedule_plan.json`

| Field | Type | Description |
|-------|------|-------------|
| `execution_plan` | list | Ordered list of scheduled job objects |
| `execution_plan[].position` | integer | 1-based position in execution order |
| `execution_plan[].job_id` | string | Unique job identifier |
| `execution_plan[].category_id` | string | Job category name |
| `execution_plan[].priority` | integer | Job priority (higher = more important) |
| `execution_plan[].duration` | integer | Job duration in time units |
| `execution_plan[].depends_on` | list | List of dependency job IDs |
| `total_jobs_scheduled` | integer | Total number of jobs in the plan |
| `total_duration` | integer | Sum of all job durations |
| `critical_path_depth` | integer | Longest dependency chain depth |
| `category_counts` | object | Number of jobs per category |
| `category_counts.compute` | integer | Compute job count |
| `category_counts.io` | integer | IO job count |
| `category_counts.maintenance` | integer | Maintenance job count |

### `/app/runtime/output/resource_report.json`

| Field | Type | Description |
|-------|------|-------------|
| `epoch_resources` | object | Per-category duration from final processing epoch |
| `epoch_resources.compute` | integer | Compute duration in final epoch |
| `epoch_resources.io` | integer | IO duration in final epoch |
| `epoch_resources.maintenance` | integer | Maintenance duration in final epoch |
| `total_jobs` | integer | Total jobs processed |
| `categories_scheduled` | list | Sorted list of category names with scheduled jobs |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Configuration with category list, scheduling parameters, and output settings |
| `/app/runtime/job_loader.py` | Loads and filters job definitions from CSV category files |
| `/app/runtime/scheduler_engine.py` | Resolves dependencies, sorts by priority, and computes epoch resources |
| `/app/runtime/plan_builder.py` | Constructs structured output from scheduling results |
| `/app/runtime/run_scheduler.py` | Main entry point orchestrating the full process |
| `/app/runtime/data/compute_jobs.csv` | Compute job definitions (20 entries) |
| `/app/runtime/data/io_jobs.csv` | IO job definitions (18 entries) |
| `/app/runtime/data/maintenance_jobs.csv` | Maintenance job definitions (17 entries) |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The data files are correct — the bugs are in the Python source code and its interaction with the configuration file. Focus on:

- How category names are parsed from the configuration
- Which configuration section provides scheduling epoch parameters
- How epoch resources are aggregated across processing epochs
- How jobs with identical priorities are ordered for execution
