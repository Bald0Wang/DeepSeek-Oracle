---
name: post-dev-security-review
description: Perform post-implementation security review on recent code changes and produce prioritized hardening recommendations with file evidence and fix guidance. Use when a development task is completed, before merge/release, or when users ask for security checks, vulnerability analysis, or security optimization suggestions for backend/frontend/API/worker code.
---

# Post Dev Security Review

## Overview

Review changed code after implementation and output actionable security improvements, not generic advice. Focus on real attack paths, impact, and concrete mitigation steps tied to specific files.

## Review Workflow

1. Identify change scope.
- Prefer `git status --short` and `git diff --name-only`.
- If no diff is available, ask the user which files were changed and continue.

2. Triage by risk.
- Prioritize auth, permission checks, input validation, secrets, file/command execution, DB queries, external HTTP calls, and LLM provider integrations.
- Review changed dependencies and lockfiles for supply-chain risk.

3. Run a checklist-driven assessment.
- Use `references/deepseek-oracle-security-checklist.md`.
- Apply only sections relevant to touched files and stack components.

4. Produce a structured report.
- Start with findings sorted by severity: `Critical`, `High`, `Medium`, `Low`.
- For each finding include: risk, exploit path, impact, file evidence, and fix guidance.
- If no blocking issue is found, still provide hardening improvements and tests.

## Output Contract

Use this structure exactly:

### Findings
- `[Severity] Title`
- `Risk:` What can go wrong.
- `Attack path:` How an attacker could exploit it.
- `Impact:` Data, integrity, availability, or cost consequences.
- `Evidence:` `path/to/file:line`.
- `Fix:` Specific remediation; include patch-style suggestions when useful.

### Security Optimization Suggestions
- Provide 3-5 concrete improvements, prioritized by risk reduction and implementation cost.
- Tie each suggestion to one or more changed files.

### Verification Steps
- List commands/tests to validate the mitigation.
- Include at least one negative test (malicious input or unauthorized case).

## Quality Rules

- Avoid vague statements like "improve security" without code-level direction.
- Do not report speculative vulnerabilities without evidence; mark assumptions explicitly.
- Prefer smallest safe change first, then optional stronger hardening.
- Always mention secret handling and sensitive logging exposure if relevant to changed files.
- For LLM/provider code, check key leakage, prompt injection exposure, unsafe tool access, and unbounded external calls.

## References

- Read `references/deepseek-oracle-security-checklist.md` before finalizing conclusions.
