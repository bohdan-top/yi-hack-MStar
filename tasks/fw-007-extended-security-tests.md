# FW-007 — extended security tests

- Status: Planned
- Milestone: 0.3.0
- Priority: P1
- Dependencies: FW-002; FW-005
- Target: y203c / 6FUS

## Scope

Expand tests for API authorization, CSRF, command construction, secret leakage, service exposure, config migration, malformed protocol inputs and dependency regressions. Use controlled fixtures and authorized test devices only. Document threat model and residual risks.

## Acceptance criteria

Repeatable automated suite and sanitized evidence; findings tracked with severity and remediation; hardware tests reported separately.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
