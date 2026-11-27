# FW-012 — safe upgrade and release gates

- Status: Planned
- Milestone: 0.1.0
- Priority: P0
- Dependencies: FW-001; FW-002; FW-003; FW-004; FW-007.1
- Target: y203c / 6FUS

## Scope

Document exact y203c initial install, SD-based local update and rollback steps from upstream wiki; verify actual fw_upgrade.sh behavior, layout, size, checksum, config preservation and version compatibility. Disable upstream automatic/update download behavior for the fork. Preserve Wi-Fi and security settings safely; distinguish healthy-system downgrade from brick recovery. Prepare correct stock recovery images, backups and power-loss precautions; keep private artifacts offline. Require explicit owner approval before each physical flash; use non-sensitive scenes. Before daily use, test cold boot without WAN, motion clips and playback, authenticated RTSP from phone with concurrent recording, reconnect, power cycle, SD capacity/cleanup, 72-hour soak and independent network capture. If RTSP remains unreliable, fix it before deployment; recording-only is not an equivalent acceptance for the requested profile.

## Acceptance criteria

Before first flash: build and static gates pass, validated recovery inputs and documented recovery plan, external isolation and explicit approval. Before daily use: hardware gates pass, no critical unmitigated risk, config migration and local update path verified as far as safely possible; report NOT VERIFIED for untested brick recovery. Subsequent releases require rollback readiness, checksums, regression results and explicit approval.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
