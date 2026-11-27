# FW-001 — sanitized execution report

Date: 2026-11-27. Status: **BLOCKED — local Windows checks and public downloads executed; firmware compilation NOT RUN.**

## Revisions and scope

- Firmware source: `c8582405b2c3c0e3b80219b0e71e21785a482867` (upstream 0.5.8, y203c / 6FUS).
- Tested implementation and workflow definition: `5a05439df718e2d1d7b93f9cf5a0fdfe7c9a2306`. The working files tested were committed as this revision without implementation changes afterward. The report/evidence update is a separate commit.
- Branch: `feature/fw-001-baseline-build`; existing draft [PR #3](https://github.com/bohdan-top/yi-hack-MStar/pull/3), base `firmware/y203c` at `0fc8aff82ba94adb58d2932bd860912ea2aca4d3`.
- Publication used the authenticated GitHub connection after Git CLI required interactive authentication. The published implementation tree `bb8173bae3ef1e5e598ad3ff3a9c598fabfdfff4` exactly matches the tested local implementation tree.
- Workflow execution revision: **none**. No hosted workflow dispatched; local results are not CI results.
- Source comparison against the pinned commit found no changes to upstream firmware files. All nine recursive Git dependencies match the inventory. The clean onvif submodule was restored to its pinned gitlink after switching branches; no local submodule edits were discarded.
- This report supersedes the previous remote-sandbox blocker report. Its machine-readable measurements and public archive hashes are in [local evidence](fw-001-local-evidence.json). Raw logs, manifests and downloaded archives remain outside Git.

## Actual host environment

Windows `10.0.26200.9911`; PowerShell `7.6.9`; Python `3.12.10`; Git `2.52.0.windows.1`; Git Bash `5.2.37`. The host has 16 logical processors and 68,295,344,128 bytes of physical RAM. The selected data volume is NTFS with roughly 3.35 TB free, exceeding the initial 40 GiB budget.

WSL `2.6.3.0`, kernel `6.6.87.2-1`, is installed. The only registered distribution observed was the stopped Docker Desktop distribution, with storage outside the selected data root. No dedicated build distribution is registered. Docker CLI `29.1.3` is installed; the Desktop engine connection fails because the engine is not running. This is not an operational isolated build environment.

The requested data root did not exist before this run. Task directories, public dependency audit cache, scratch scripts, test temporary data and reports were created on the selected alternate disk. No SDK, stock archives, builder archive or approved private lock was supplied there. No approved lock digest or reviewed private-input provenance was provided. The upstream README's SDK filename and third-party Docker image reference are not independent license/provenance evidence; neither was used to construct a builder.

There is no user .wslconfig file. A shared swap-placement configuration change and any necessary shared VM restart require owner approval under FW-001 section 6. No WSL configuration, existing distro placement, Docker Desktop settings or shared services were changed. No Docker image was pulled or loaded. The missing distro blocks the real host request before any WSL command executes; swap and private approval gates remain additional prerequisites.

## Executed checks

Subprocess wall time is measured with Python `time.perf_counter`; host internal time uses a .NET Stopwatch. Durations include interpreter startup and test fixture I/O. These are prerequisite/test measurements, not build durations.

| Local command/check | Exit | Seconds | Interpretation |
| --- | ---: | ---: | --- |
| Windows host regressions | 0 | 3.886 | Expected result |
| FW-001 synthetic tests | 0 | 3.400 | Expected result |
| FW-008 synthetic tests | 0 | 16.264 | Expected result |
| Offline wrapper Bash syntax | 0 | 0.093 | Expected result |
| Download guard Bash syntax | 0 | 0.058 | Expected result |
| Public inventory preflight | 0 | 0.127 | Expected result |
| Hosted full request fails closed | 1 | 0.152 | Expected result |
| Actual Windows build request | 1 | 0.869 | Expected result |

Total measured final verification interval, including source and gitlink checks: **26.840 seconds**. The host's own report measured **0.199 seconds** and returned `WSL_DISTRO_MISSING` at the WSL distribution stage.

- Windows host checks: **28 assertions passed**, including new/missing path ancestors, junction rejection, cleanup retaining the junction target, WSL extended-path normalization, swap placement, duplicate configuration keys, private diagnostic filtering, report sanitization and real missing-distro rejection.
- FW-001: **7 tests passed**, covering resource/isolation command arguments, cache selection and corrupt-cache recovery, interrupted download cleanup, atomic checkpoint replacement, verified checkpoint reuse, changed settings/tampered outputs, unexpected URLs, and Windows execution rejection before input access. Network interruptions use injected exceptions and synthetic data, not a terminated firmware compile.
- FW-008: **10 tests passed; 2 Linux symlink fixtures explicitly skipped on Windows**. Synthetic output member/byte checks still ran. Linux symlink checks and the complete Linux suite must run in the dedicated distro before acceptance.
- The unexpected-download shell guard was actually executed in Git Bash and rejected wget even when its failure was ignored by the calling shell. This is shell guard evidence only; no Docker network namespace or actual container behavior was tested.
- Both infrastructure shell syntax checks passed. Public inventory preflight passed; it does not validate private inputs. The hosted full request deliberately failed closed. The real Windows build command with 6 CPUs and 8 GiB requested exited 1 at the missing-distro gate.

## Public input verification and cache observations

Nine exact HTTPS archives were downloaded into the alternate-disk audit cache and SHA-256 checked against separately published candidate digests. Two previously missing pins were resolved before downloading: wolfSSL 5.9.2 from the immutable [Buildroot manifest](https://github.com/buildroot/buildroot/blob/45a0ce557d9508f437dd196eb95107958283abf5/package/wolfssl/wolfssl.hash), whose adjacent recipe selects the same GitHub archive tag; wireless-tools 29 from the immutable [OpenWrt recipe](https://github.com/openwrt/openwrt/blob/d69b2830681fdaeb2b19b28231e9171684ead6d1/package/network/utils/wireless-tools/Makefile). Both observed byte streams match those independent hashes.

The cold audit downloaded **45,323,507 bytes** in **5.125 seconds** with up to three concurrent downloads. A second pass rehashed all nine cached files: **9 verified cache hits, 0 downloaded bytes**. This audit cache is not an approved private input lock and is not a completed FW-001 Linux runner cache exercise. The production cache helper was tested with synthetic inputs separately.

| Public input | Bytes | Verified SHA-256 |
| --- | ---: | --- |
| `src/busybox/busybox-1.36.1.tar.bz2` | 2525473 | `b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314` |
| `src/jq/jq-1.8.1.tar.gz` | 2026798 | `2be64e7129cecb11d5906290eba10af694fb9e3e7f9fc208a311dc33ca837eb0` |
| `src/onvif_simple_server/crypt-1.18.2.tar.xz` | 2638064 | `96ad4c3b8336050993c5bc2cf6c057484f2b0f9f763448151567fbab5e767b84` |
| `src/onvif_simple_server/mbedtls-3.6.5.tar.bz2` | 5367178 | `4a11f1777bb95bf4ad96721cac945a26e04bf19f57d905f241fe77ebeddf46d8` |
| `src/onvif_simple_server/v5.9.2-stable.tar.gz` | 28078586 | `2f4ef3d4fd387a9b3191d36a6316d69116c46ff69bb9583b6c82b36d7b8ca114` |
| `src/onvif_simple_server/zlib-1.3.2.tar.gz` | 1502830 | `bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16` |
| `src/onvif_simple_server/json-c-0.18.tar.gz` | 401788 | `876ab046479166b869afc6896d288183bbc0e5843f141200c677b3e8dfb11724` |
| `src/rRTSPServer/v2.0.1.tar.gz` | 2488373 | `a4142815d8d52d0e798212a5adea54ecf42bcd4eec8092b37a8cb615ace91dc6` |
| `src/wireless_tools/wireless_tools.29.tar.gz` | 294417 | `6fb80935fe208538131ce2c4178221bab1078a1656306bce8909c19887e2e5a1` |

Four public digests remain unresolved: Dropbear 2026.91, the candidate immutable mdnsd ZIP, live555 2023.01.19, and tinyalsa 1.0.0. Publisher/package metadata lookups did not establish independent hashes for these exact bytes; hashes from other versions were rejected as substitutes. mdnsd's historical equivalence to the official firmware build also remains unproved. No newly observed hash was automatically approved. Transitive prerequisites still need the actual approved builder and offline build to establish completeness.

## Storage and resource measurements

During the final local check interval, free bytes on the data volume changed from **3350836621312** to **3350836621312**; the system volume changed from **81531367424** to **81530712064**. These are whole-volume snapshots and include unrelated host activity; they do not prove absence of system-disk writes. Task-owned file sizes changed from **45384113** to **45385027 bytes**. Test temporary files were **0 bytes before and 0 bytes after**; this is not a peak temporary-storage measurement. The measured footprint covers only completed local checks/public audit, not the future SDK, distro, Docker storage or builds. Retain the initial 40 GiB free-space budget.

CPU affinity/quota, 8 GiB memory and no container swap are configured and unit-tested as Docker arguments. Make/nproc wrappers are present; actual compilation parallelism and cgroup enforcement are **NOT VERIFIED**. No compiler or container ran, so peak build CPU, peak build/container RAM, peak temporary storage, ARM executable ABI/device compatibility and build stage timings are **unmeasured**. No GPU was requested. Whole-WSL RAM/CPU limits were not altered.

## Firmware artifacts and acceptance

**No `home_y203c`, `sys_y203c` or `y203c_0.5.8.tgz` firmware artifacts were generated. No firmware artifact hashes exist.** Public dependency hashes above are not firmware hashes.

| Acceptance area | Actual result |
| --- | --- |
| Operational isolated WSL2/native Docker | BLOCKED: dedicated distro absent; Desktop engine stopped and data placement unsuitable |
| Licensed compatible SDK/toolchain and immutable builder | BLOCKED: no approved private inputs or license/provenance evidence |
| ARM smoke/ABI test | NOT RUN |
| Complete approved lock/all inputs/local private preflight | BLOCKED; four public hashes plus private inputs and review remain outstanding |
| Actual Docker isolation/effective CPU/RAM and parallelism | NOT RUN; command construction and shell denial only tested |
| Full offline compilation/three artifacts | NOT RUN |
| JFFS2 integrity/partition limits/model/version/archive/official-release comparison | NOT RUN; full validation implementation still incomplete |
| Independent fresh repeat/reproducibility analysis | NOT RUN; no reproducibility claim |
| Windows one-command runner | Executed locally and failed closed at a measured prerequisite gate |
| Checkpoint/cache/interruption recovery | Synthetic helper tests passed; public audit cache reused; real build interruption/repeat NOT RUN |
| Alternate disk and cleanup | Public audit/tests executed there; task-owned test cleanup verified; distro/Docker/build placement not demonstrated |
| Sanitized timing/storage evidence | This report and JSON; resource and scope limitations explicit |
| Restricted input and camera safety | Only code, documentation and sanitized public evidence staged; no proprietary inputs committed, camera accessed or firmware flashed |

FW-008 remains the sole firmware build entrypoint. The full FW-001 runner intentionally continues to return nonzero even if two output sets are produced, until JFFS2/partition/model/release/isolation checks and reproducibility explanations are implemented and verified. This run does not close that implementation limitation or any unverified acceptance criterion.

## Required unblock and decision

Obtain the licensed MSC3XX SDK/GCC 4.8.3 inputs with trusted provenance and usage rights, verified stock filesystem archives for `4.5.0.0C_201910080934`, and a complete independently approved lock with its trust-anchor digest. Resolve the remaining public/transitive inputs without self-approving observed hashes. Approve a shared WSL swap placement beneath the selected data root (or disabled swap), plus a restart only if needed to apply it; the runner will not edit global settings. Then provision the dedicated ext4 distro/native Docker on the alternate disk, finish validation implementation and execute the real primary/repeat builds and container tests.

Keep FW-001 **blocked** and PR #3 **draft**. No merge, release approval, camera modification or flashing is authorized by these local results.
