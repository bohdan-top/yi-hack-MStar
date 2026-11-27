# FW-010 — local api

- Status: Planned
- Milestone: 0.4.0
- Priority: P2
- Dependencies: FW-006; FW-007; FW-009
- Target: y203c / 6FUS

## Scope

Design minimal authenticated local API for status, recording index and stream access with least privilege, strict allowlists, redacted secrets, safe methods, CSRF controls and bounded inputs. Prefer a trusted external gateway for TLS if device resources are insufficient. Do not open WAN access.

## Acceptance criteria

Documented API and threat model; authorization and negative tests; no regression of privacy, recording or live viewing.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
