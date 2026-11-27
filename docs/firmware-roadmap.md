# Firmware roadmap — y203c local-first fork

Status: planning only. No firmware modifications, builds, installation or hardware validation are included in this change.

## Goal and constraints

Support the YI 1080p Home YYS.2016, target y203c, serial prefix 6FUS, stock firmware 4.5.0.0C_201910080934. Scope the first release to this target. Local motion-triggered SD recording (64 GB FAT32 candidate), authorized live viewing from Android over the home network, optional audio, no mandatory vendor cloud or account. Confidentiality and reliable recordings take precedence over convenience. No public WAN exposure, no automatic deployment, no secrets or device-derived proprietary images committed to this public fork.

## Baseline and branch policy

Upstream stable tag [0.5.8](https://github.com/roleoroleo/yi-hack-MStar/releases/tag/0.5.8), commit `c8582405b2c3c0e3b80219b0e71e21785a482867`, is the initial build reference. The fork's master is already ahead of that tag; this documentation PR targets master without reverting it. FW-001 must build the exact tag first; create a separate implementation/release branch from the pinned baseline or explicitly reconcile the newer master changes after reviewing and recording them. Never reset master or silently use a moving upstream. Keep task branches/PRs small; pin all imported fixes and review independently. Use fork-specific versions and never advertise these as upstream releases.

## Milestones

| Release | Scope | Gate |
| --- | --- | --- |
| 0.1.0 | Security baseline: FW-001, 002, 003, 004, 007.1, 012 | Controlled initial flash only after pre-flash checks. Daily use only after hardware acceptance including stable phone viewing. |
| 0.2.0 | Stability: FW-006 | Longer soak, RTSP and SD regression tests; pull forward blocking fixes into 0.1.0. |
| 0.3.0 | Hardening: FW-005, 007, 008, 009 | Dependency audit, extended tests, manual CI and signed artifacts. Pull forward critical reachable fixes. |
| 0.4.0 | Optional features: FW-010, 011 | Local API and optional client, only if needed. |

## Task index

| ID | Task | Milestone | Priority | Dependencies |
| --- | --- | --- | --- | --- |
| FW-001 | [baseline build](../tasks/fw-001-baseline-build.md) | 0.1.0 | P0 | None |
| FW-002 | [cgi and cloud patches](../tasks/fw-002-cgi-and-cloud-patches.md) | 0.1.0 | P0 | FW-001 |
| FW-003 | [secure defaults](../tasks/fw-003-secure-defaults.md) | 0.1.0 | P0 | FW-001; FW-002 |
| FW-004 | [cloud isolation](../tasks/fw-004-cloud-isolation.md) | 0.1.0 | P0 | FW-001; FW-002; FW-003 |
| FW-005 | [dependency hardening](../tasks/fw-005-dependency-hardening.md) | 0.3.0 | P1 | FW-001; FW-007.1 |
| FW-006 | [rtsp and recording stability](../tasks/fw-006-rtsp-and-recording-stability.md) | 0.2.0 | P1 (minimum stability gate P0) | FW-001; FW-003; FW-004; FW-012 |
| FW-007.1 | [minimum security tests](../tasks/fw-007.1-minimum-security-tests.md) | 0.1.0 | P0 | FW-002; FW-003 |
| FW-007 | [extended security tests](../tasks/fw-007-extended-security-tests.md) | 0.3.0 | P1 | FW-007.1; FW-005 |
| FW-008 | [manual ci build](../tasks/fw-008-manual-ci-build.md) | 0.3.0 | P1 | FW-001; FW-007.1 |
| FW-009 | [release provenance](../tasks/fw-009-release-provenance.md) | 0.3.0 | P1 | FW-001; FW-008 |
| FW-010 | [local api](../tasks/fw-010-local-api.md) | 0.4.0 | P2 | FW-006; FW-007; FW-009 |
| FW-011 | [optional dotnet client](../tasks/fw-011-optional-dotnet-client.md) | 0.4.0 | P3 | FW-010 |
| FW-012 | [safe upgrade and release gates](../tasks/fw-012-safe-upgrade-and-release-gates.md) | 0.1.0 | P0 | FW-001; FW-002; FW-003; FW-004; FW-007.1 |

## Execution order and safety gates

Start FW-001. Review security patches and test design next; then secure configuration and isolation, minimum tests and release/recovery gate. FW-012 coordinates readiness rather than treating successful compilation as approval to flash. Initial controlled hardware evaluation and deployment approval are separate. Use a trusted router/firewall with WAN deny (IPv4/IPv6), separate camera segment, only authorized client traffic; a camera-side blacklist alone is insufficient. Disable Web UI outside isolated administration windows; RTSP is plaintext and must stay inside the controlled network. If local viewing or motion recording fails, or there is an unmitigated critical reachable defect, do not deploy. No private video/audio in logs or test artifacts.

Every task PR must include scope, pinned inputs, changes, test commands/results, residual risks and NOT VERIFIED items. Keep a release report with SHA-256, exact target, recovery plan, hardware matrix, upgrade and rollback evidence. Subsequent upgrades should be local via SD/manual mechanism, preserving safe settings; no factory restore required when supported by verified upgrade path. Do not assume atomic update or guaranteed rollback.

## Evidence and known gaps

- [Upstream #595](https://github.com/roleoroleo/yi-hack-MStar/issues/595): equals-sign parsing fix is present in the 0.5.8 tag; regression-test it.
- [Upstream #597](https://github.com/roleoroleo/yi-hack-MStar/issues/597): reported RTSP regression on 6FUS; must be tested on actual hardware.
- [Upstream #600](https://github.com/roleoroleo/yi-hack-MStar/issues/600), [#601](https://github.com/roleoroleo/yi-hack-MStar/issues/601), [#605](https://github.com/roleoroleo/yi-hack-MStar/issues/605): CGI validation issues; proposed fixes #602, #603, #606.
- [Upstream #604](https://github.com/roleoroleo/yi-hack-MStar/pull/604): hosts/DNS blacklist fix; retained vendor processes and network egress require separate controls.
- [Manual firmware upgrade](https://github.com/roleoroleo/yi-hack-MStar/wiki/Manual-firmware-upgrade) and [stock firmware build inputs](https://github.com/roleoroleo/yi-hack-MStar/blob/0.5.8/stock_firmware/README.md).
- Closed vendor binary behavior, actual release binary equivalence, SD reliability and brick recovery are NOT VERIFIED. Recheck all upstream PR status and advisories during implementation.
