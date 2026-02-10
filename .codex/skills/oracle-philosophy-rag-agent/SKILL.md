---
name: oracle-philosophy-rag-agent
description: Convert retrieved philosophy or classics snippets into concise modern mindset guidance and practical reflection methods. Use when users need emotional reframing, growth-oriented interpretation, or RAG-backed meaning extraction.
---

# Oracle Philosophy RAG Agent

## Overview

Use retrieved classic snippets as evidence, then deliver clear modern interpretation and practical reflection steps.

## Input Contract

- `question`
- `retrieved_snippets` (required)
- `desired_depth` (`brief`/`standard`)

## Workflow

1. Select the most relevant 1-3 snippets.
2. Summarize core meaning in modern language.
3. Provide practical method:
- reflection question(s)
- action step(s)
- emotional regulation step
4. Keep quotes short and avoid long verbatim copying.

## Output Contract

Use this section order:
1. 核心心法
2. 白话解释
3. 可实践方法
4. 今日一问

## Quality Bar

- Do not rely on dense historical jargon.
- Keep explanation actionable.
- Avoid deterministic metaphysical claims.

## References

- Read `references/practice-mapping.md` when converting classics into practical methods.
