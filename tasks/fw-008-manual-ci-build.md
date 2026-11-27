# FW-008 — manual ci build

- Status: Planned
- Milestone: 0.3.0
- Priority: P1
- Dependencies: FW-001; FW-007.1
- Target: y203c / 6FUS

## Scope

Implement manual workflow_dispatch build/test for y203c with least-privilege permissions, pinned actions/toolchain inputs, artifact retention and no stock images or secrets committed. Use local/self-hosted build where licensing or private inputs prevent hosted builds; isolate untrusted PRs from runners. No automatic device deployment.

## Acceptance criteria

Manual run builds and tests target, exports logs/manifests and checksums; failure blocks release; no device access from CI.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
