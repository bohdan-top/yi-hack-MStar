# FW-001 — Baseline Firmware Build

- **Status:** Blocked — dedicated WSL/native Docker, real isolation/resource probes and all Linux tests passed; licensed private inputs/approval and remaining firmware validation are outstanding.
- **Milestone:** 0.1.0
- **Priority:** P0
- **Dependencies:** FW-008
- **Target:** y203c / 6FUS
- **Baseline:** upstream yi-hack-MStar 0.5.8
- **Source commit:** `c8582405b2c3c0e3b80219b0e71e21785a482867`

## Objective

Establish a verified, repeatable local firmware build environment and successfully compile the unmodified upstream firmware for the target camera using the shared build entrypoint introduced in FW-008.

Complete all stages within a single task and implementation PR, using incremental commits.

## 1. Local Build Environment

- Inspect the existing Windows, WSL2 and Docker environment.
- Install or configure missing prerequisites.
- Obtain the compatible MStar MSC3XX SDK and ARM GCC 4.8.3 cross-compilation toolchain from trusted sources.
- Verify licenses, provenance, checksums and compatibility.
- Create a reproducible, version-pinned Docker builder.
- Compile a minimal ARM executable and verify its architecture, ABI and compatibility with the target firmware.
- Export the verified builder image and record its immutable image ID and SHA-256.

Reuse existing compatible components where possible.

## 2. Build Inputs and Dependencies

- Resolve all outstanding dependencies from the FW-008 input inventory, including transitive downloads.
- Obtain and independently verify missing archive checksums.
- Verify recursive Git submodule commits.
- Prepare verified stock firmware filesystem archives for y203c, version `4.5.0.0C_201910080934`.
- Verify archive integrity and compatibility.
- Complete and review the private input lock manifest.
- Execute the local preflight using the FW-008 entrypoint.
- Verify actual Docker isolation and rejection of unexpected downloads.

Keep proprietary SDK files, stock firmware, private inputs and sensitive logs outside Git.

Do not bypass checksum verification or approve unresolved inputs merely to complete the build.

## 3. Baseline Firmware Compilation

- Use the exact pinned upstream source commit.
- Execute the full offline build through the FW-008 entrypoint.
- Investigate and resolve environment, toolchain and dependency-related failures.
- Preserve upstream firmware source files unchanged.
- If a source modification is unavoidable, document it separately as a patched build rather than a pristine baseline.
- Generate the following private artifacts:
  - `home_y203c`
  - `sys_y203c`
  - `y203c_0.5.8.tgz`
  - Build metadata and SHA-256 checksums.

Do not report success unless all required artifacts are generated and validated.

## 4. Firmware Artifact Validation

- Verify JFFS2 filesystem structure and integrity.
- Verify target identifiers and firmware version.
- Validate image sizes against the documented target partition limits.
- Verify archive contents and checksums.
- Compare output structure and relevant contents against the official upstream 0.5.8 release.
- Perform an independent second build in a clean workspace.
- Compare artifact hashes and explain any nondeterministic differences.

Do not claim bit-for-bit reproducibility unless demonstrated.

## 5. Automation and Documentation

- Provide a single-command PowerShell entrypoint for Windows that invokes the verified WSL2/Docker build procedure.
- Support configurable paths for private inputs, build cache and outputs.
- Reuse verified cached dependencies without unnecessary downloads.
- Generate a sanitized build report automatically.
- Document all prerequisites, commands, environment versions, input provenance, execution results and remaining limitations.
- Record the firmware source, build entrypoint and workflow revisions separately.

## 6. Resource Management and Autonomous Execution

- Provide configurable Windows/WSL2 storage locations for the SDK, private inputs, verified dependency cache, builder archives, staging/temp directories and outputs. Support an alternate local disk to avoid filling the system SSD. Keep Linux build workspaces on a Linux-compatible filesystem; document supported WSL2 distribution and Docker data-disk placement. Do not silently relocate existing distributions, Docker data or user files.
- Check free disk space on all affected volumes before downloads, staging and builds; report estimated and actual storage needs. Recommend an initial 40 GB free-space budget, adjustable to measured requirements.
- Expose configurable build CPU and memory limits, initially 4–6 logical CPUs and 8 GB RAM. Bound parallel compilation (including upstream make/nproc usage) and container resources. Do not require GPU resources. Document effective limits and distinguish container limits from whole-WSL usage. Do not silently edit global .wslconfig, change shared Docker settings or restart existing services; request approval if such changes are necessary.
- Make the one-command runner non-interactive for routine stages, with clear per-stage progress, exit codes and actionable failure summaries. Stop at genuine blockers such as missing trusted SDK provenance, required license acceptance, administrator approval, or approval of private inputs; never automatically bypass these gates.
- Persist stage checkpoints outside Git, keyed by source/entrypoint revisions, input-lock digest, builder identity and relevant settings. Resume from the last verified successful stage after interruption or failure. Revalidate cached artifacts and invalidate dependent stages when inputs change. Provide an explicit clean/rebuild option. The independent repeat-build validation must use a fresh build workspace and must not reuse compiled outputs or skip compilation through checkpoints.
- Reuse only digest-verified cached downloads and approved builder inputs. Download again if verification fails; do not bless newly observed hashes. Preserve approved private inputs and successful outputs.
- Clean up only task-owned disposable files, with explicit opt-in for deleting retained cache data. Do not run broad Docker prune commands, delete unrelated files or remove existing WSL distributions. Retain useful private failure logs for diagnosis.
- Include measured wall-clock time per stage and total, peak observed CPU/RAM usage, disk usage before/after and peak temporary storage where measurable, downloaded bytes and cache-hit/resume results in the sanitized report. Identify measurement scope, sampling method and unmeasured values; distinguish estimates from observed results. Do not publish private paths, credentials or restricted artifacts.

## Acceptance Criteria

- [x] WSL2 and Docker environment operational.
- [ ] Compatible SDK and ARM toolchain verified.
- [ ] ARM cross-compilation smoke test passed.
- [ ] All required build inputs verified.
- [ ] Private input lock manifest complete and approved.
- [ ] Local preflight passed.
- [x] Docker isolation verified using the public environment probe and shared FW-008 flags; SDK builder execution remains pending.
- [ ] Full offline firmware build passed.
- [ ] All required firmware artifacts generated.
- [ ] Filesystem, partition size and archive validation passed.
- [ ] Independent repeat build completed.
- [ ] Reproducibility results documented.
- [ ] Single-command local build available.
- [x] Sanitized execution report committed; it explicitly records that firmware compilation has not run.
- [ ] Alternate-disk storage and configurable paths demonstrated without unintended system-disk growth.
- [ ] CPU/RAM limits and bounded compilation parallelism configured and verified.
- [ ] Interrupted execution resumes from verified checkpoints; changed or tampered inputs invalidate affected stages.
- [ ] Verified dependency cache reused; independent repeat build does not reuse compiled outputs.
- [ ] Cleanup confined to task-owned disposable files.
- [ ] Autonomous routine execution demonstrated; approval and provenance blockers fail closed.
- [ ] Sanitized timing and resource-usage report includes actual measurements and measurement limitations.
- [x] No proprietary inputs or sensitive data committed.
- [x] No camera modifications or flashing performed.

## Execution Rules

- Use one feature branch: `feature/fw-001-baseline-build`.
- Use one implementation PR with incremental commits, following the [roadmap](../docs/firmware-roadmap.md) branch policy: base firmware implementation on `firmware/y203c` created from the pinned upstream commit, with only the reviewed roadmap, task and CI bootstrap files transferred; do not merge master into the firmware branch.
- Reuse FW-008 infrastructure rather than introducing a parallel build pipeline.
- Automatically resolve routine implementation and environment issues where safe.
- Explicitly report genuine external blockers and unverified requirements.
- Do not weaken security or supply-chain controls to achieve a successful build.
- Do not proceed to firmware installation or release approval.

## Definition of Done

A verified local environment can repeatedly build the baseline y203c firmware from approved inputs using the shared offline build pipeline.

All acceptance criteria are satisfied, and the implementation and sanitized evidence are committed for independent review.

Successful compilation does not authorize flashing. Security hardening and release approval remain within FW-002 and FW-012.
