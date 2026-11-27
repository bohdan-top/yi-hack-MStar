# FW-001 — baseline build

- Status: Planned
- Milestone: 0.1.0
- Priority: P0
- Dependencies: None
- Target: y203c / 6FUS

## Scope

Build the unmodified upstream 0.5.8 tag (c8582405b2c3c0e3b80219b0e71e21785a482867) for y203c, not the moving master branch. Use a documented Linux/WSL2 environment; inventory SDK/toolchain, stock images and submodule commits. Verify input digests and licenses; keep device-derived images and secrets outside Git. Record build commands, logs, output SHA-256, image layout and size checks. Compare release outputs where possible and explain nondeterminism; do not claim bit-for-bit reproducibility unless proven.

## Acceptance criteria

A clean build produces both y203c images and a local update archive; manifest identifies all known inputs; independent repeat build and comparison results documented. No flashing.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
