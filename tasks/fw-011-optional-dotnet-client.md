# FW-011 — optional dotnet client

- Status: Planned
- Milestone: 0.4.0
- Priority: P3
- Dependencies: FW-010
- Target: y203c / 6FUS

## Scope

Prototype optional .NET/MAUI client for local live viewing and recordings. Prefer established local RTSP client first. Store credentials in platform secure storage; no analytics or cloud by default, no remote port forwarding. Remote access only via separately controlled VPN if ever requested.

## Acceptance criteria

Local playback and recordings on Android; no unwanted egress or credential logs; clear reconnect/error state.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
