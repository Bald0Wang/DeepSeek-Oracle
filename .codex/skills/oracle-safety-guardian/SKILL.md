---
name: oracle-safety-guardian
description: Classify oracle inputs/outputs into risk levels and return allow, rewrite, or refuse policy with concrete constraints. Use before and after specialist-agent generation, especially for finance, medical, legal, violence, self-harm, or fear-marketing risks.
---

# Oracle Safety Guardian

## Overview

Perform two-stage safety governance for oracle content: pre-check user input and post-check generated output.

## Input Contract

- `mode`: `pre` or `post`
- `content`: user query or generated answer
- `context`: optional (profile summary, intent, tool trace)

## Workflow

1. Classify risk using `references/risk-grading.md`.
2. Return decision:
- `allow`
- `rewrite`
- `refuse`
3. If `rewrite`, provide strict rewrite constraints.
4. If `refuse`, provide safe alternative guidance.

## Output Contract

Return structured policy:
- `risk_level`: `S0`/`S1`/`S2`/`S3`/`S4`
- `decision`: `allow`/`rewrite`/`refuse`
- `reasons`: short list
- `constraints`: list of mandatory constraints
- `disclaimer_level`: `none`/`light`/`strong`

## Mandatory Rules

- Never output direct investment buy/sell instructions.
- Never output medical diagnosis or treatment plan.
- Refuse illegal, violent, or self-harm instructions.
- Block fear-marketing and paid-disaster-relief narratives.

## References

- Read `references/risk-grading.md` before final decision.
