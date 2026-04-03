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
- `datasets/edge_case_resumes_fixed.json`
- `datasets/edge_case_jobs_fixed.json`
- `datasets/edge_case_histories_fixed.json`
- `datasets/edge_case_cases.json`
- `datasets-new/*.json` (Langfuse dataset specs)

Each fixture includes `notes` and `last_reviewed` for drift tracking.

## Langfuse Datasets (8 total)
The Langfuse datasets are defined in `datasets-new/` and map to subsets of the local fixtures:
- `resume_critic_cases`
- `resume_critic_edge_cases`
- `content_strength_cases`
- `content_strength_edge_cases`
- `job_alignment_cases`
- `job_alignment_edge_cases`
- `interview_coach_cases`
- `interview_coach_edge_cases`

Create the datasets in Langfuse:
```bash
python evals/create_langfuse_datasets.py
```

Run experiments from Langfuse datasets:
```bash
python evals/run_langfuse_datasets.py --dataset resume_critic_cases
```

Run all 8 datasets:
```bash
python evals/run_langfuse_datasets.py
```

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
