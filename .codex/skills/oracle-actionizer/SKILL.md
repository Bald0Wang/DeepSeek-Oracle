---
name: oracle-actionizer
description: Transform oracle guidance into concrete, calendar-ready tasks with suggested time windows, effort level, and practical notes. Use after ZiWei/MeiHua/Tarot outputs when users need execution plans.
---

# Oracle Actionizer

## Overview

Convert abstract guidance into concrete tasks users can actually complete.

## Input Contract

- `guidance_text`
- `time_horizon` (today/this-week/this-month)
- `user_constraints` (optional)

## Workflow

1. Extract actionable intents from guidance.
2. Convert each intent into a small task.
3. Add suggested time window and expected duration.
4. Add one-line rationale and one gentle note.

## Output Contract

Return 3-5 tasks in this shape:
- `task`
- `when`
- `duration`
- `note`

Also include:
- `priority_order`
- `first_step_under_10_min`

## Quality Bar

- Every task must be specific and finishable.
- Avoid command tone; use suggestion tone.
- Prefer behavior-level actions over abstract slogans.
