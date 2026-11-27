# FW-006 — rtsp and recording stability

- Status: Planned
- Milestone: 0.2.0
- Priority: P1 (minimum stability gate P0)
- Dependencies: FW-001; FW-003; FW-004; FW-012
- Target: y203c / 6FUS

## Scope

Investigate upstream [#597](https://github.com/roleoroleo/yi-hack-MStar/issues/597), especially 6FUS versus BFUS, and [#593](https://github.com/roleoroleo/yi-hack-MStar/issues/593), [#594](https://github.com/roleoroleo/yi-hack-MStar/issues/594). Test standard RTSP over TCP with VLC Android, audio off/on, motion recording concurrently, reconnect, CPU/memory and frame gaps. Validate FAT32 64 GB media and full-card cleanup, power loss, timekeeping, offline boot; verify actual MP4 video/audio. Do not confuse NVR-remux failures with SD recording. Evaluate upstream RTSP refactors separately, avoid unverified attachment binaries. Cry detection optional and not a safety guarantee.

## Acceptance criteria

For first release pass minimum gates in FW-012 or keep deployment blocked; for 0.2.0 record at least seven days of soak evidence, reproducible stress tests, recording/stream gap metrics and no unresolved material recording or live-view failure.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
