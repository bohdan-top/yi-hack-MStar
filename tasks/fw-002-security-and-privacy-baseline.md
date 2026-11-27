# FW-002 — Security & Privacy Baseline

- Status: Planned
- Milestone: 0.1.0
- Priority: P0
- Dependencies: FW-001
- Target: y203c / 6FUS

## Scope and execution order

Deliver one integrated minimum security and privacy baseline after the pristine baseline build. The five sections replace the former standalone FW-002, FW-003, FW-004, FW-007.1 and FW-005.1 tasks; none of their requirements or gates is waived. Design tests alongside patches, implement A–C, integrate D, then complete E against the exact candidate; iterate until all software gates pass. Use separate logical commits for each section and review the integrated diff. No intermediate partially secured release or physical flash. FW-012 independently verifies the final release candidate and coordinates the first controlled flash and hardware-only acceptance.

### A. CGI and cloud patches

Review upstream PRs [602](https://github.com/roleoroleo/yi-hack-MStar/pull/602), [603](https://github.com/roleoroleo/yi-hack-MStar/pull/603), [604](https://github.com/roleoroleo/yi-hack-MStar/pull/604), [606](https://github.com/roleoroleo/yi-hack-MStar/pull/606) at implementation time. Pin commits, apply minimal changes or equivalent fixes, and document upstream status. Validate canonical recording directories and basenames, allowlist config types/keys, prevent path traversal and unsafe shell argument expansion. Address or disable unsafe state-changing endpoints; include CSRF protection if exposed. Verify the prior sed injection fix and equals-sign regression. Do not treat the hosts fix as an egress firewall.

**Acceptance criteria**

Negative and positive regression cases pass in a disposable fixture; no file outside allowed paths is read, modified or removed; legitimate operations still work; unresolved security defects and mitigations recorded.

### B. Fail-closed secure defaults

Default to offline recording, disable Telnet, FTP, SSH, ONVIF, discovery, MQTT, upload, speaker and unnecessary endpoints. Do not expose anonymous RTSP or Web UI during bootstrap; define a local provisioning procedure with unique credentials. Provide an opt-in RTSP-only profile for the trusted phone, high stream and optional audio, no Internet. Document how to administer again safely after disabling HTTP/SSH; never bake passwords into images or logs. Change both `system.conf` and `script/check_conf.sh` fallback defaults. Inspect startup/service logic and restored `.fw_upgrade` configurations. Validate settings before starting any network listener or vendor process: missing, empty, malformed, truncated, duplicate or legacy keys and missing/invalid credentials must fail closed for network exposure and cloud. Preserve valid local recording settings where possible and provide isolated reprovisioning. No hard-coded/default credential fallback. Apply the same fail-closed validation and authorization to every service start, restart and start-all path (including `service.sh`, CGI service control and alternate RTSP implementations), not just boot; reject disabled services and invalid credentials without opening listeners. Disable automatic execution of SD-card custom startup scripts (including `/tmp/sd/yi-hack/startup.sh`) and unverified executable overrides by default; audit all boot paths and SD hooks, including stock components. Reject or sanitize legacy `CRONTAB` and other command-bearing configuration before use. Protect credential-bearing configuration and temporary files on filesystems supporting permissions (owner-only access, restrictive umask); avoid passwords in logs, URLs, diagnostics and process arguments where feasible, documenting and mitigating unavoidable exposure.

**Acceptance criteria**

Fresh, missing, empty, truncated, malformed, duplicate-key and migrated config tests pass, including upgrade restore and reboot; missing/invalid credentials prevent RTSP/admin startup; insecure legacy settings cannot silently re-enable disabled services or cloud; no unauthenticated video/snapshot/admin endpoint in enabled profile; only explicitly allowed ports reachable, including after direct start/restart/start-all requests; untrusted SD startup hooks and migrated command-bearing settings cannot execute automatically; credential files have restrictive permissions where supported, and sanitized diagnostics contain no credentials; recovery/admin path documented.

### C. Cloud isolation

Inspect startup branches including retained proprietary cloud process. Preserve local motion recording while minimizing cloud components. Provide a deployment firewall contract: independent router denies camera WAN IPv4/IPv6 and new camera-to-LAN sessions; restrict DNS to local needs, allow local DHCP/NTP as needed and trusted client RTSP over TCP. Keep remote exposure, UPnP and port forwarding disabled. Assess device firewall capabilities as defense in depth, not the sole boundary. Capture traffic from an independent network point during cold boot, idle, motion, live view and reconnect. Use non-sensitive test scenes.

**Acceptance criteria**

External firewall verified before any private use; no successful WAN connections in tests; DNS forwarding cannot leak camera queries; attempted traffic documented; local recording and authorized viewing work without WAN or vendor login. If not, NO-GO.

### D. Minimum automated security tests

Create isolated tests for CGI path validation, traversal rejection, unsafe config keys, password parsing, expected valid requests, auth defaults and service enablement. Use disposable fixtures and mocked destructive commands; no destructive probes against the physical camera. Integrate the suite into the FW-008 manual pipeline so failures block the release gate. Add fail-closed configuration tests for missing, empty, malformed, truncated, duplicate and legacy keys, including restored settings. Define upgrade-integrity negative tests (wrong target, corrupted/untrusted archive, unexpected paths and interrupted staging); tests needing the FW-012 implementation may be specified here and executed in FW-012 rather than creating a circular dependency. Test direct service start/restart/start-all with disabled services or invalid credentials, untrusted SD startup hooks and migrated command-bearing settings in isolated fixtures; check credential-file permissions and redaction. Record skipped/unsupported cases.

**Acceptance criteria**

Runnable documented local test command, negative and positive cases, exit code on failure, reviewable sanitized report. Every critical mitigation has a test or an explicit hardware-only gate. No skipped mandatory software test counts as a pass; FW-012 reruns the suite against the final candidate.

### E. Minimum dependency security triage

Before any first flash, inventory actual shipped executables, libraries, kernel/libc, retained proprietary components and external build inputs for the exact release candidate. Record versions, hashes, build options and reachable interfaces, including RTSP/LIVE555, BusyBox, HTTP/CGI during provisioning, and vendor services. Check relevant current advisories against actual versions/configuration and reachability, including boot, provisioning and upgrade states. Explicitly mark unknown versions and closed components; document exposure and mitigation evidence. Absence of published advisories is not proof of safety.

Record each finding with source/date, affected version, severity, reachability, remediation or mitigation and verification evidence. Pull necessary fixes into 0.1.0 without waiting for FW-005; disable unsafe optional services. Block release on known critical reachable defects or unresolved high-risk reachable exposures without verified effective mitigation. Repeat triage after changes to the final candidate; verify actual runtime exposure in FW-012 controlled hardware acceptance.

**Acceptance criteria**

Reviewed candidate-specific inventory and advisory disposition, effective mitigation evidence, no unresolved critical reachable defect or unmitigated high-risk reachable exposure, and explicit pre-flash GO/NO-GO. Hardware-only validation remains pending until FW-012. Broader dependency upgrades and full SBOM work remain in FW-005/FW-009.

## Integrated acceptance criteria

- All five sections' software acceptance criteria pass; hardware-only items remain explicitly pending FW-012. No skipped mandatory software test counts as a pass.
- A reviewed candidate build, sanitized regression results, documented network-isolation deployment contract, candidate-specific dependency disposition and documented residual risks are available. Independent live network capture, actual device isolation and recording/viewing verification occur during FW-012; do not claim hardware verification beforehand.
- Minimum security suite is integrated into the FW-008 manual pipeline. Upgrade tests requiring FW-012 are specified here and executed at the final release gate, without a circular prerequisite.
- No critical reachable defect or unresolved high-risk reachable exposure without verified effective mitigation. If blocked, fix the candidate or keep release at NO-GO.
- Repeat affected tests and triage after any candidate change, including fixes implemented in FW-012.

## Deliverables

Implementation PR with logical commits, pinned patch provenance, configuration and isolation instructions, reviewed inventory/advisory disposition report, test commands and sanitized results, residual risks and explicit NOT VERIFIED items. Link back to the [roadmap](../docs/firmware-roadmap.md). No device changes without explicit owner approval.
