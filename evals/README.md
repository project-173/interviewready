# Evals

Dataset version: `0.1.0`

## Overview
This package provides shared fixtures and loaders for:
- LLM-as-judge regression tests
- Batch eval runs via `evals/run_evals.py`

## Dataset Layout
- `datasets/resumes.json`
- `datasets/job_descriptions.json`
- `datasets/histories.json`
- `datasets/cases.json`

Each fixture includes `notes` and `last_reviewed` for drift tracking.

## Run Naming
Recommended run name format:
- `evals/{agent}/{dataset_version}/{date}` for batch runs
- `live/{agent}/{intent}/{date}` for sampled live evals

`date` should be in `YYYY-MM-DD` format.

## Updating Fixtures
When fixtures change:
1. Update `notes` and `last_reviewed` for modified fixtures.
2. Bump `dataset_version` in this file.
3. Keep a soft cap of 6 cases per agent.
4. Retire superseded cases instead of growing unbounded.
