# FW-009 — release provenance

- Status: Planned
- Milestone: 0.3.0
- Priority: P1
- Dependencies: FW-001; FW-008
- Target: y203c / 6FUS

## Scope

Create release manifest with fork version, pinned upstream commit, patch provenance, toolchain, dependency hashes, per-artifact SHA-256, SBOM, license notices and detached signatures/attestations. Define independent verification before local installation, key rotation and rollback policy. Distinguish host-side signing from bootloader enforcement. Minimal checksums and manifest are mandatory from 0.1.0.

## Acceptance criteria

Verification script rejects changed artifacts and wrong target; signed releases trace to exact reviewed code; no claim of on-device signature enforcement without proof.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
