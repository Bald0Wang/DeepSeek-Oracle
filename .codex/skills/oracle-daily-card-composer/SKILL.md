---
name: oracle-daily-card-composer
description: Compose daily oracle cards from profile, date context, and recent conversation themes using a fixed stable format. Use for daily home feed generation, ritual cards, and lightweight recurring guidance.
---

# Oracle Daily Card Composer

## Overview

Generate a concise daily card with stable structure and actionable tone.

## Input Contract

- `user_profile_summary`
- `date_context` (weekday, solar term, festival if any)
- `recent_topics`
- `daily_seed` (required for reproducibility)

## Workflow

1. Lock output with `daily_seed` to keep same-day stability.
2. Generate card in fixed sections.
3. Keep guidance lightweight and executable.
4. Add 3 optional follow-up questions.

## Output Contract

Always output these sections:
1. 关键词
2. 今日倾向
3. 今日宜（1-3 条）
4. 今日忌（1-2 条）
5. 可追问（3 条）

## Quality Bar

- Same seed + same date must produce same core conclusion.
- No disaster assertion.
- Keep total length compact for product cards.
