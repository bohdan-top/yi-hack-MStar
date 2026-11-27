# FW-001 — sanitized execution report

Date: 2026-11-27. Status: **BLOCKED — native WSL/Docker, Linux regressions and real constrained-container probes passed; firmware compilation NOT RUN.**

## Revisions and evidence scope

Firmware source: `c8582405b2c3c0e3b80219b0e71e21785a482867`, upstream 0.5.8, y203c / 6FUS. Branch `feature/fw-001-baseline-build`, existing draft [PR #3](https://github.com/bohdan-top/yi-hack-MStar/pull/3), base `firmware/y203c`. Upstream firmware files remain unchanged; all nine recursive gitlinks were verified in the earlier local run.

The shared FW-008 entrypoint, FW-001 build runner and workflow definition remain unchanged from `5a05439df718e2d1d7b93f9cf5a0fdfe7c9a2306`. The newly executed environment-probe script has SHA-256 `ba837d02d3ed4d90660a585c24f7041321ce7de7f9ade0813aa2e579aa7d5562` and is included with this evidence update. Workflow execution revision: **none**; no hosted workflow dispatched.

[Current environment evidence](fw-001-environment-evidence.json) contains exact runtime observations. [Earlier Windows/public dependency evidence](fw-001-local-evidence.json), committed in `b93a3ff4b02a58e7e4ba831468566efe54f85214`, remains historical evidence for the nine verified public archives and Windows checks. Its missing-distro and unmeasured-container statements were true at that earlier stage and are superseded by this continuation. Raw logs, archives and private inputs remain outside Git.

## Approved WSL provisioning actually executed

The owner explicitly approved shared WSL swap placement. A new .wslconfig points swap to the selected alternate-disk data root. No configuration existed previously; no forced shared WSL shutdown was needed. Existing distributions and Docker Desktop data were not moved. No global WSL CPU/RAM settings were changed.

A new `FirmwareBuild` WSL2 distribution was installed on the data disk from Ubuntu 24.04.5 amd64. Rootfs SHA-256 `bb415d824822c4b878125729af451a5d18fb13d1cf5cbed9a7393ad64ac6039e` matched both [Microsoft's distro inventory](https://github.com/microsoft/WSL/blob/master/distributions/DistributionInfo.json) and [Canonical's release checksums](https://releases.ubuntu.com/24.04.5/SHA256SUMS) before installation. The initial WSL download failed with `0x80072efe`; a resumable HTTPS download recovered the operation without disabling TLS or checksum verification.

Native Docker and host prerequisites were installed using Ubuntu's authenticated package metadata. Provisioning measured **250.138 seconds**, excluding the earlier rootfs download/import. Observed Linux Python `3.12.3`, kernel `6.6.87.2-microsoft-standard-WSL2`, Docker Engine `29.1.3`. Exact package versions are in the JSON evidence. Native dockerd, its local Unix socket, Docker storage, containerd storage and owner-only staging were verified on the dedicated ext4 filesystem backed by the data-disk VHD. Active VM swap is 8 GiB; its configured backing VHD is on the selected data disk. Container swap is separately limited to zero.

The distro VHD measured **2,998,927,360 bytes** and swap VHD **37,748,736 bytes** of file length. This is not an allocation or peak-storage claim. Whole data-volume free space changed from **3350836604928** to **3346621800448 bytes** during this continuation; unrelated activity may contribute. A system-volume baseline and peak temporary storage were not measured, so zero system-disk growth is not claimed. All intentional large task downloads, image archives, distro/Docker data, caches, temporary work and artifacts were placed on the alternate disk. Keep the initial 40 GiB free-space budget for future SDK/build work.

## Complete Linux checks

Both suites ran in the actual dedicated Linux distro using private ext4 temporary storage: **7 FW-001 tests and 12 FW-008 tests passed, zero skips**. The two symlink fixtures previously skipped on Windows now passed. Both Bash syntax checks and the environment-probe CLI check passed.

| Check | Exit | Wall seconds |
| --- | ---: | ---: |
| FW-001 Linux suite | 0 | 3.154 |
| FW-008 Linux suite | 0 | 0.865 |
| offline wrapper syntax | 0 | 0.037 |
| download guard syntax | 0 | 0.035 |
| environment probe CLI syntax | 0 | 0.254 |

These are measured subprocess durations, not firmware build timings. Earlier Windows evidence remains 28 host assertions passed, 7 FW-001 tests passed, and 10 FW-008 tests passed with two Windows-only skips. Tests cover verified cache reuse, corrupted cache recovery, atomic checkpoint writes, interruption cleanup, provenance/output tampering, unexpected downloads and source/archive checks with synthetic fixtures.

## Real offline Docker isolation and limits

The public Python image is a test runtime only, **not the SDK builder**. A stalled native Docker CDN transfer was stopped and recovered through Windows HTTPS. The official OCI index, amd64 manifest, config, all four compressed layers and all uncompressed diff IDs were verified before import. Compressed layer bytes: **45,269,859**; prepared Docker archive bytes: **128,460,800**, SHA-256 `f91993b6dfcc1c8878d48887ce028ac208cf583194fa17931ea82f8c6316dcb2`. The verified image preparation measured **23.547 seconds**.

Registry config digest: `sha256:f4a31709c79ea38eafccf1234211e87d36625b5f9752d3df28319b43b48c0f23`. Official amd64 manifest digest: `sha256:1475c4f5b6bcb7d35e57661d6f5d7429ec4041275633c15f2b49350ac898276d`. Docker 29 containerd imports use an imported manifest identity rather than the legacy config identity. The first config-ID lookup failed closed; before execution, the loaded image was exported again and its manifest/config/layer graph independently rehashed against the already authenticated contents. Verified native runtime ID: `sha256:fb5b23e71c65e126bb2dd9c8bdcf612d54ffff59767893cfad303a633446443f`. No newly observed ID was accepted merely because Docker printed it; no private builder lock was approved. This distinction must be reviewed when preparing the real builder. See [Docker's containerd image-store documentation](https://docs.docker.com/engine/storage/containerd/).

The probe uses the shared `fw008.docker_args` function, immutable image ID, `--pull=never`, no network, read-only root and inputs, task-owned writable workspace, dropped capabilities, no-new-privileges, 6 CPU affinity/quota and 8 GiB memory with no container swap. Actual in-container assertions passed:

- Affinity: **6 logical CPUs**; cgroup CPU quota/period **600000/100000**.
- cgroup memory maximum **8589934592 bytes**; swap maximum **0 bytes**.
- `nproc=6`, `MAKEFLAGS=-j6`, and FW-008 job environment match the requested parallelism. Upstream compilation/make-wrapper behavior remains unexecuted.
- Only loopback exists; an external TCP connection failed; the actual download guard rejected wget even when the caller ignored its failure.
- Root and input writes failed with EROFS. No MTD devices were present. Seccomp filtering and no-new-privileges were active; effective capabilities were exactly `0xB` (CHOWN, DAC_OVERRIDE, FOWNER), matching FW-008's allowed set.

A real probe container was forcibly killed after reaching the running state: exit **137**, no completed output accepted, task workspace removed. The cold-start interruption race discovered during testing was fixed by timing from the observed running state. A subsequent fresh offline container used a new workspace and passed all checks. Both successful probe workspaces were cleaned, and the final native inventory found **zero task-owned probe containers remaining**. Retained images/cache were not pruned.

| Actual probe | Wall seconds | Samples | Peak sampled CPU | Peak sampled RAM |
| --- | ---: | ---: | ---: | ---: |
| Forced interruption and cleanup | 17.236 | 2 | 597.37% | 159,383,552 bytes |
| Fresh complete offline probe | 24.261 | 5 | 599.77% | 159,068,979 bytes |

Sampling used `docker stats --no-stream` plus a 0.5-second wait. Docker CPU percentages count 100% per logical CPU, so roughly 600% means six busy CPUs; sampled percentages are accounting-window observations, not a separate quota test. The workload allocated 128 MiB and ran six CPU workers for eight seconds. It did not test allocation at the 8 GiB OOM threshold. These are sampled **probe** peaks; firmware build CPU/RAM peaks, build wall times and peak temporary storage remain unmeasured. Whole-WSL limits were not changed. No GPU was requested.

## Public dependency cache

The earlier run actually downloaded nine exact public archives (45,323,507 bytes), matched independent published candidate hashes and rehashed nine warm-cache hits with zero downloaded bytes. Their full SHA-256 values and timings remain in [historical local evidence](fw-001-local-evidence.json). Newly resolved pins were wolfSSL 5.9.2 from [Buildroot](https://github.com/buildroot/buildroot/blob/45a0ce557d9508f437dd196eb95107958283abf5/package/wolfssl/wolfssl.hash) and wireless-tools 29 from [OpenWrt](https://github.com/openwrt/openwrt/blob/d69b2830681fdaeb2b19b28231e9171684ead6d1/package/network/utils/wireless-tools/Makefile).

Four exact public archive digests remain unresolved: Dropbear 2026.91, the candidate immutable mdnsd ZIP, live555 2023.01.19 and tinyalsa 1.0.0. mdnsd historical equivalence and transitive offline prerequisites remain unproved. No unresolved digest or private input was automatically approved.

## Current blocker and acceptance

The actual Windows build entrypoint was rerun with 6 CPUs / 8 GiB. It now passes distro/VHD and swap placement checks and fails closed at **`INDEPENDENT_INPUT_APPROVAL_REQUIRED`**. No licensed MSC3XX SDK/GCC 4.8.3 provenance, verified stock filesystem archives, SDK builder archive, complete approved private lock or trust-anchor digest has been supplied to the task. Public runtime/image verification does not satisfy these private firmware prerequisites.

| Acceptance area | Current evidence |
| --- | --- |
| Operational WSL2/native Docker | PASS for the dedicated alternate-disk environment |
| Actual Docker isolation and CPU/RAM kernel settings | PASS for the public probe using shared FW-008 flags; SDK builder not executed |
| Linux regressions and task-owned cleanup | PASS; 19 tests without skips, actual interruption/fresh probe, zero probe containers left |
| SDK/toolchain licensing, approved builder and complete private inputs/lock | BLOCKED; no supplied approved private inputs, four public digests unresolved |
| ARM compiler/ABI smoke | NOT RUN |
| Local private preflight and full offline firmware compilation | NOT RUN; actual Windows request rejected at input approval |
| Three firmware artifacts and firmware SHA-256 values | NONE GENERATED |
| JFFS2/partition/model/version/official-release validation | NOT RUN; validation implementation remains incomplete |
| Independent fresh firmware repeat/reproducibility/build checkpoint recovery | NOT RUN; container probes and synthetic checkpoints are not firmware builds |
| Firmware timing/peak CPU/RAM/peak temporary storage | Unmeasured; only prerequisite and probe observations recorded |
| No proprietary inputs committed/no camera operations | Verified change scope contains code and sanitized public evidence; no flashing, camera access or merge performed |

**No `home_y203c`, `sys_y203c` or `y203c_0.5.8.tgz` firmware artifacts exist from this execution. No firmware hashes or reproducibility claim can be made.** FW-008 remains the sole firmware build entrypoint. The full FW-001 runner still intentionally returns nonzero if outputs are produced but the remaining acceptance validation has not been completed.

Keep FW-001 **blocked** and PR #3 **draft**. Continue once trusted licensed SDK/toolchain and stock inputs, remaining provenance and an independently approved lock/digest are available; then finish validation implementation and execute the primary/repeat firmware builds. The shared swap approval has already been applied and does not need to be requested again.
