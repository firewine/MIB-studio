# M0 Security Review

Decision: GO
Reviewer: Codex Security Agent
Date: 2026-06-21
Scope: local auth, CORS, keychain, PII masking, teacher packet approval, egress SSRF/DNS guard, audit scope.

## Blocking Issues

None.

## Non-Blocking Issues

- Egress uses `PinnedDNSHTTPTransport`; raw `httpx.Client(base_url=origin)` is forbidden.
- v0 audit storage is local SQLite with redaction, OS user permissions, and retention. DB encryption-at-rest is Enterprise/v0.2+.
- Teacher Packet approval is reserved atomically with `dataset_gen/generation_mode=teacher_synthetic` Job creation.
- HF model catalog token may live only in ignored local `.env` for Day-0 fill; app/API/teacher credentials still use keychain and are not stored in `.env`.
- Profile-specific pip-audit runs in GitHub security workflow; local verify-only records explicit skip artifacts when the audit tool is unavailable.

## Missing Tests

None blocking for M0. Security matrix is listed in `SECURITY_SPEC §19.9`.

## Spec Updates Required

None.

## Assumptions

Production accepts only bootstrap auth mode.
