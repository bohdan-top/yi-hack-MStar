# FW-008 — manual CI build bootstrap

- Status: Planned
- Milestone: 0.1.0
- Priority: P0 (first implementation task)
- Dependencies: None
- Target: y203c / 6FUS

## Scope

Create a manual GitHub Actions workflow (`workflow_dispatch` only) and a shared local Linux/WSL2 build entrypoint for y203c. Inspect upstream build scripts and prerequisites first. Separate the workflow revision from the firmware source ref: default the initial baseline build to upstream 0.5.8 (`c8582405b2c3c0e3b80219b0e71e21785a482867`), and support explicitly selected reviewed fork revisions for later builds. Record resolved commits and submodule revisions.

- Use least-privilege permissions, pinned actions, documented toolchain/SDK inputs and explicit preflight checks for required files, checksums, tools and target.
- Provide manual preflight and full-build modes. Missing SDK or stock images must produce an actionable failure for full builds, not a false success or an empty firmware artifact.
- Keep proprietary/device-derived stock images, secrets and private logs outside the public repository and public workflow artifacts. Use a trusted local build or isolated self-hosted runner if legal or private inputs prevent hosted builds; never give untrusted PRs runner access. Do not expose restricted binaries through artifacts.
- Export sanitized diagnostics, build metadata and checksums of permitted outputs; retain artifacts for a bounded period. No automatic releases, deployment, camera access or flashing.
- Document how to manually run the workflow, including the requirement for a workflow_dispatch definition on the default branch, and the supported local fallback. Use the same entrypoint to avoid divergent build procedures.

## Acceptance criteria

The workflow and local entrypoint are reviewable and manually runnable; preflight and missing-input failure paths are tested and documented. Workflow syntax is validated. No push, pull_request or scheduled build trigger. No false green for a requested full build that did not compile. Actual successful full firmware compilation, output layout and baseline comparison are FW-001 acceptance criteria, not a circular prerequisite for this bootstrap. FW-007.1 later integrates minimum security tests into the manual pipeline; FW-012 requires successful build and tests before release.

## Deliverables

Workflow, shared entrypoint, input contract, usage instructions, sanitized test evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
