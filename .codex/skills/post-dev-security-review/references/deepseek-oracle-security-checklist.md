# DeepSeek-Oracle Security Checklist

Use this checklist against changed files only. Prioritize findings that are exploitable with realistic attacker input.

## 1. API And Input Validation (Flask)

- Validate all request fields by type, range, enum, and requiredness.
- Reject unexpected keys to avoid mass-assignment issues.
- Normalize and bound date/time/gender fields before downstream calls.
- Ensure error responses do not leak stack traces, secrets, or provider details.
- Add rate limiting for expensive endpoints and async task creation routes.

## 2. AuthN/AuthZ And Task Access

- Ensure history/result endpoints enforce ownership checks.
- Prevent IDOR on task ID based APIs.
- Require explicit authorization for export and history retrieval.
- Avoid relying on client-side checks for permission decisions.

## 3. LLM Provider And Prompt Safety

- Keep API keys in environment variables only; never log raw keys.
- Validate provider/model names against an allowlist.
- Cap retries, timeouts, and max token limits to prevent abuse/cost blowup.
- Sanitize or redact user PII in prompts and logs.
- Treat model output as untrusted input before rendering or storing.

## 4. Database And Storage

- Use parameterized SQL only; never construct SQL via string concat.
- Verify migrations do not weaken constraints or indexes used for ownership checks.
- Ensure exported markdown/report files cannot escape intended directories.
- Avoid storing sensitive plaintext unless necessary and documented.

## 5. Worker/Queue/Redis

- Validate job payloads before enqueue and before worker execution.
- Set retry policy with bounded attempts and backoff.
- Avoid deserializing untrusted data formats unsafely.
- Protect Redis access with network isolation and credentials in deployment.

## 6. Node iztro Service

- Validate `date`, `timezone`, `gender` strictly before calling `astro`.
- Return safe generic errors; avoid exposing internal exceptions.
- Add body size limit and request timeout.
- Avoid enabling permissive CORS by default in production.

## 7. Frontend (React + Markdown)

- Treat backend content as untrusted when rendering markdown.
- Prevent XSS: sanitize HTML or disable raw HTML rendering.
- Avoid storing secrets/tokens in local storage.
- Ensure API base URL and env handling do not expose internal endpoints unintentionally.

## 8. Dependency And Supply Chain

- Review `requirements.txt`, `package.json`, and lockfiles in the diff.
- Flag new unpinned/high-risk dependencies.
- Suggest running `pip-audit` and `npm audit --production`.

## 9. Logging And Observability

- Log security-relevant events: auth failures, permission denials, throttling.
- Redact secrets and personal data in logs.
- Include request ID/task ID for incident tracing.

## 10. Report Severity Guide

- Critical: remote code execution, auth bypass, secret leakage with direct compromise path.
- High: exploitable injection, IDOR on sensitive data, persistent XSS, major privilege escalation.
- Medium: missing validation, excessive data exposure, weak operational limits.
- Low: defense-in-depth gaps and hardening opportunities.
