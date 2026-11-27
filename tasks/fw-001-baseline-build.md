# FW-001 — baseline build

- Status: Planned
- Milestone: 0.1.0
- Priority: P0
- Dependencies: FW-008
- Target: y203c / 6FUS

## Scope

Build the unmodified upstream 0.5.8 tag (c8582405b2c3c0e3b80219b0e71e21785a482867) for y203c, not the moving master branch. Use the manual CI workflow and shared local build entrypoint established in FW-008, with a documented Linux/WSL2 environment; inventory SDK/toolchain, stock images and submodule commits. Use the FW-008 input lock manifest and verified-input-only build path. Verify input digests and licenses; keep device-derived images and secrets outside Git. Record workflow, entrypoint and firmware source commits separately. Any unavoidable source modification is a separate identified patched build, not the pristine baseline. Record build commands, logs, output SHA-256, image layout and size checks. Compare release outputs where possible and explain nondeterminism; do not claim bit-for-bit reproducibility unless proven.

## Acceptance criteria

A successful manually triggered full build (or documented private/local runner execution of the same entrypoint when hosted builds are blocked by input licensing) produces both y203c images and a local update archive; manifest identifies all inputs including transitive downloads and resolved submodules; independent repeat build and comparison results documented. No flashing.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
