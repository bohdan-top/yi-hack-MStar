# FW-003 — secure defaults

- Status: Planned
- Milestone: 0.1.0
- Priority: P0
- Dependencies: FW-001; FW-002
- Target: y203c / 6FUS

## Scope

Default to offline recording, disable Telnet, FTP, SSH, ONVIF, discovery, MQTT, upload, speaker and unnecessary endpoints. Do not expose anonymous RTSP or Web UI during bootstrap; define a local provisioning procedure with unique credentials. Provide an opt-in RTSP-only profile for the trusted phone, high stream and optional audio, no Internet. Document how to administer again safely after disabling HTTP/SSH; never bake passwords into images or logs. Verify migrated configs cannot silently enable cloud or insecure defaults.

## Acceptance criteria

Fresh and migrated config tests pass; no unauthenticated video/snapshot/admin endpoint in enabled profile; only explicitly allowed ports reachable; recovery/admin path documented.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
