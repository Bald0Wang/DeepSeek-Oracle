---
name: oracle-consistency-auditor
description: Audit consistency of repeated long-line oracle outputs and diagnose drift causes across routing, retrieval, and generation settings. Use when validating long-term ZiWei responses, regression testing, or before release quality gates.
---

# Oracle Consistency Auditor

## Overview

Evaluate whether repeated outputs for the same long-line query remain stable at conclusion, recommendation direction, and safety reminders.

## Input Contract

- `test_case_id`
- `prompt`
- `profile_summary`
- `outputs` (2+ candidate outputs)
- `run_metadata` (model, temperature, retrieval scope, routing trace)

## Workflow

1. Extract each output into 3 layers:
- `main_conclusion`
- `advice_direction`
- `risk_disclaimer`
2. Score pairwise consistency with `references/scoring-rubric.md`.
3. Diagnose drift source: routing, retrieval, generation randomness, or memory summary.
4. Provide fix plan ranked by impact.

## Output Contract

Return:
- `consistency_score` (0-100)
- `layer_scores` (conclusion/advice/risk)
- `drift_causes` (ranked)
- `fixes` (P0/P1/P2)
- `verification_steps`

## Quality Bar

- Never claim drift without textual evidence.
- Keep evidence snippets short and comparable.
- Recommend minimal effective changes first.

## References

- Read `references/scoring-rubric.md` before scoring.
