# FW-012 — safe upgrade and release gates

- Status: Planned
- Milestone: 0.1.0
- Priority: P0
- Dependencies: FW-002
- Target: y203c / 6FUS

## Scope

Document exact y203c initial install, SD-based local update and rollback steps from upstream wiki; verify actual fw_upgrade.sh behavior, layout, size, checksum, config preservation and version compatibility. Disable upstream automatic/update download behavior for the fork. Preserve Wi-Fi and security settings safely; distinguish healthy-system downgrade from brick recovery. Prepare correct stock recovery images, backups and power-loss precautions; keep private artifacts offline. Require explicit owner approval before each physical flash; use non-sensitive scenes. Before daily use, test cold boot without WAN, motion clips and playback, authenticated RTSP from phone with concurrent recording, reconnect, power cycle, SD capacity/cleanup, 72-hour soak and independent network capture. If RTSP remains unreliable, fix it before deployment; recording-only is not an equivalent acceptance for the requested profile.

### Update integrity and credential handling

Before any destructive operation or staging into flash-visible paths, independently verify the archive against a trusted reviewed release manifest (host-side verification mandatory from 0.1.0; an accompanying untrusted checksum is insufficient). Verify target y203c, compatible version/layout, member names/types/sizes and per-image digests. Reject invalid, extra, duplicate, absolute/traversal paths, symlinks/hardlinks, special files and oversized members; validate and extract only into an isolated temporary location, check every operation and abort safely on failure. If reliable on-device verification is infeasible, disable the CGI updater and require a verified host-side SD-only procedure. Do not claim bootloader signature enforcement.

Inventory credential-bearing backups including `.fw_upgrade` on FAT32. Minimize plaintext copies, protect offline backups, clean temporary files on success and handled failure, and document residual exposure after interruption (FAT32 permissions/deletion are not secure erasure). Revalidate restored settings before starting or restarting network services; no insecure legacy fallback. Restore only allowlisted data files and validated settings, not executable hooks or arbitrary command-bearing settings such as legacy `CRONTAB`. Verify that untrusted SD startup scripts and executable overrides remain disabled across upgrade, reboot and rollback. Set restrictive ownership/permissions on credential-bearing configuration, password files and temporary files where supported; verify that secrets are absent from release evidence and diagnostic logs. Document any unavoidable credential exposure on FAT32 or through process arguments and the required mitigations.

## Acceptance criteria

Before first flash: build and static gates pass, candidate-specific FW-002 minimum dependency triage is complete and final FW-002 minimum security suite passes (including update integrity tests or equivalent host-side tests if CGI updater is disabled), validated recovery inputs and documented recovery plan, external isolation and explicit approval. Before daily use: hardware gates pass, including runtime service restart enforcement, SD hook and migration safety, and credential handling checks, no critical unmitigated risk, config migration and local update path verified on the controlled device or through a documented safe SD procedure; do not advertise upgrade readiness if unverified; report NOT VERIFIED for untested brick recovery. Subsequent releases require rollback readiness, independent artifact verification, regression results and explicit approval. Implement and test minimum RTSP/recording fixes in 0.1.0 if needed for daily use even when broader FW-006 work remains planned for 0.2.0.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
