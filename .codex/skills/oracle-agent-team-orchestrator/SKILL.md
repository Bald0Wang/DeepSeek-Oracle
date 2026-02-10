---
name: oracle-agent-team-orchestrator
description: Orchestrate DeepSeek Oracle multi-agent workflows by routing user intents to specialist oracle skills, enforcing safety gates, and composing one unified answer with follow-up questions and action items. Use when requests involve long-term ZiWei, short-term MeiHua, tarot, daily card, philosophy RAG, or mixed multi-domain queries.
---

# Oracle Agent Team Orchestrator

## Overview

Route each user request to the right specialist skill, run mandatory safety checks, and return one unified response that is calming, actionable, and compliant.

## Input Contract

Require these inputs (fill missing values with `null`):
- `user_query`
- `conversation_history_summary`
- `user_profile_summary`
- `selected_school` (`east`/`west`/`mixed`)
- `enabled_schools` (e.g. `ziwei,meihua` for MVP)
- `safety_policy`

## Workflow

1. Run pre-check with `$oracle-safety-guardian`.
2. Classify intent:
- Long-term life trend -> `$oracle-ziwei-agent`
- Short-term event -> `$oracle-meihua-agent`
- Symbolic reflection -> `$oracle-tarot-agent` only if west mode is enabled
- Daily briefing -> `$oracle-daily-card-composer`
- Practical execution -> `$oracle-actionizer`
- Mindset/philosophy uplift -> `$oracle-philosophy-rag-agent`
3. Invoke 1-3 specialist skills only; avoid unnecessary fan-out.
4. Merge outputs using `references/response-contract.md`.
5. Run post-check with `$oracle-safety-guardian`.
6. If post-check is `rewrite` or `refuse`, follow that policy before final output.

## Output Contract

Return this JSON-shaped structure in natural language sections:
- `answer_text`
- `follow_up_questions` (exactly 3)
- `action_items` (0-5)
- `safety_disclaimer_level` (`none`/`light`/`strong`)
- `trace` (internal; called skills + reason)

## Quality Bar

- Always include: 1 calming sentence + 2-4 actionable suggestions + 1 risk reminder.
- Avoid fatalism and fear-based language.
- Keep long-line conclusions stable for the same user/profile input.
- Use Chinese by default unless user asks for another language.

## References

- Read `references/routing-matrix.md` before routing.
- Read `references/response-contract.md` before composing final output.
