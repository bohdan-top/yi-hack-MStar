# FW-005 — dependency hardening

- Status: Planned
- Milestone: 0.3.0
- Priority: P1
- Dependencies: FW-005.1; FW-007.1
- Target: y203c / 6FUS

## Scope

Extend FW-005.1 triage to a comprehensive inventory of actual shipped binaries, kernel/libc and build dependencies; map current advisories to exact versions/configuration and reachable attack surfaces. Prioritize LIVE555, BusyBox and other exposed parsers; assess upstream fixes and toolchain compatibility. Update one dependency at a time with regression tests and size checks. FW-005.1 is the mandatory earlier gate. Do not defer necessary reachable-risk mitigations to this milestone.

## Acceptance criteria

Versioned inventory/SBOM and advisory disposition; high-risk reachable defects fixed or service disabled with documented risk acceptance; build and hardware regression tests pass.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
