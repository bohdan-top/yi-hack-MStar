# FW-004 — cloud isolation

- Status: Planned
- Milestone: 0.1.0
- Priority: P0
- Dependencies: FW-001; FW-002; FW-003
- Target: y203c / 6FUS

## Scope

Inspect startup branches including retained proprietary cloud process. Preserve local motion recording while minimizing cloud components. Provide a deployment firewall contract: independent router denies camera WAN IPv4/IPv6 and new camera-to-LAN sessions; restrict DNS to local needs, allow local DHCP/NTP as needed and trusted client RTSP over TCP. Keep remote exposure, UPnP and port forwarding disabled. Assess device firewall capabilities as defense in depth, not the sole boundary. Capture traffic from an independent network point during cold boot, idle, motion, live view and reconnect. Use non-sensitive test scenes.

## Acceptance criteria

External firewall verified before any private use; no successful WAN connections in tests; DNS forwarding cannot leak camera queries; attempted traffic documented; local recording and authorized viewing work without WAN or vendor login. If not, NO-GO.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
