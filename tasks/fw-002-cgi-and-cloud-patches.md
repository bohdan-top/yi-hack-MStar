# FW-002 — cgi and cloud patches

- Status: Planned
- Milestone: 0.1.0
- Priority: P0
- Dependencies: FW-001
- Target: y203c / 6FUS

## Scope

Review upstream PRs [602](https://github.com/roleoroleo/yi-hack-MStar/pull/602), [603](https://github.com/roleoroleo/yi-hack-MStar/pull/603), [604](https://github.com/roleoroleo/yi-hack-MStar/pull/604), [606](https://github.com/roleoroleo/yi-hack-MStar/pull/606) at implementation time. Pin commits, apply minimal changes or equivalent fixes, and document upstream status. Validate canonical recording directories and basenames, allowlist config types/keys, prevent path traversal and unsafe shell argument expansion. Address or disable unsafe state-changing endpoints; include CSRF protection if exposed. Verify the prior sed injection fix and equals-sign regression. Do not treat the hosts fix as an egress firewall.

## Acceptance criteria

Negative and positive regression cases pass in a disposable fixture; no file outside allowed paths is read, modified or removed; legitimate operations still work; unresolved security defects and mitigations recorded.

## Deliverables

Implementation PR (where applicable), test commands and results, sanitized evidence, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
