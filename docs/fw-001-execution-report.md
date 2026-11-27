# FW-001 â€” sanitized execution report

Date: 2026-11-27. Status: **BLOCKED â€” native WSL/Docker, Linux regressions and real constrained-container probes passed; firmware compilation NOT RUN.**

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


## Remote continuation: structural validation and input provenance review (2026-11-27)

Added `ci/fw001/image_structure.py` and six synthetic regression tests in
`ci/fw001/test_image_structure.py`. The runner now validates both primary and
repeat JFFS2 images, including a resumed primary, before reporting comparison
results; the primary checkpoint is published only after the new checks pass.
Checks cover little-endian node magic, node/header and payload/name CRCs,
eraseblock boundaries, erased padding, and candidate partition sizes.

The candidate limits are 0xC30000 (home) and 0x1E0000 (sys), from the
[upstream backup wiki example](https://github.com/roleoroleo/yi-hack-MStar/wiki/Dump-your-backup-firmware/d5d2274c60f31421cdbd4b3ccca290b7c66d3060).
The pinned `scripts/pack_fw.sh` supplies the 64 KiB erase size and little-endian
format. These limits are not independent evidence of this particular camera's
partition geometry. The scanner is deliberately restricted to pristine
mkfs.jffs2 node types; it does not mount, decompress, reconstruct filesystem
semantics, verify the model/version files or compare official release contents.
Unsupported node types fail closed pending review. Full acceptance still
returns nonzero; no release authorization is implied.

**Executed:** six synthetic tests passed in a separate Linux execution
environment (Python unittest, 0.009 s); the tested file Git blob hashes
matched the committed files:
`7d5418ff1c1613018b37ea2b8ecc6aa5edc69d27` (validator),
`92eb2262eba3161e4908fbe85be8c4eb6f789537` (tests).
Command: `python -B -m unittest -v test_image_structure` in the isolated
test directory. The original 19 tests and the full integrated runner were not
rerun in this continuation. Real mkfs.jffs2 images and private firmware
outputs were unavailable, so the new checks are NOT VERIFIED against them.

Public source research:
- Dropbear: [Buildroot 2026.91 update](https://lists.buildroot.org/pipermail/buildroot/2026-May/801979.html)
  publishes SHA-256 for `dropbear-2026.91.tar.bz2`, not the required GitHub
  `DROPBEAR_2026.91.tar.gz`. Do not transfer its digest.
- tinyalsa: [historical Buildroot update](https://lists.buildroot.org/pipermail/buildroot/2016-November/164193.html)
  identifies v1.0.2 and an earlier commit archive; neither proves v1.0.0.
- live555: [VideoLAN mirror](https://download.videolan.org/pub/pub/testing/contrib/live555/)
  lists the requested version; a listing alone is not independent digest evidence.
- mdnsd: historical equivalence and exact archive digest remain unresolved.
- SDK: upstream README recommends the community
  [borodiliz/yi-hack image](https://hub.docker.com/r/borodiliz/yi-hack).
  This is a lead, not an authenticated licensed SDK or an approved builder.
  No proprietary download or untrusted image execution was performed.
- Stock: upstream stock_firmware/README.md requires device-derived images.
  The existing private recovery artifacts may be useful, but their contents and
  provenance must be verified locally; do not substitute a modified release.

No unresolved digest was populated and no private input lock was approved.
The environment and compilation status above remains unchanged. The new
runner revision supersedes the earlier entrypoint revision for future builds;
the earlier evidence remains historical. Use an independently reviewed new
entrypoint SHA when eventually executing the runner.


## Minimum-input continuation — 2026-11-27

**Current outcome: candidate inputs and an authenticated minimal amd64 builder
are prepared; FW-001 is awaiting independent approval. Firmware compilation,
the independent repeat and validation of newly built artifacts have NOT RUN.**
This section supersedes the earlier unresolved-dependency/full-SDK blocker;
earlier execution evidence remains historical.

- Audited 25 modules, all nine recursive gitlinks, 2,615 tracked Git files and
  181 build instruction files. No additional external vendor SDK component was
  demonstrated as a build dependency. Snapshot's FFmpeg 8.1.1 and libjpeg-turbo
  3.1.4.1 downloads were missing from the old inventory and are now included.
- All 15 public module archives have provenance-backed SHA-256 evidence.
  Rechecked all 15 cached byte streams; nine reused the earlier verified cache.
  Git-archive verification compares every file and mode against separately
  fetched source trees; it does not invent a published checksum. mdnsd's exact
  historical moving-master contents remain an explicit review caveat.
- Obtained the original Linaro GCC 4.8.3/sysroot package and verified its
  historical detached signature without relaxed GPG options. Rejected the
  community repack's unexplained termcap additions and retained original GNU
  notices. Full provenance and signature limitations are documented separately.
- Independently checked 99 exact Debian package archives against their saved
  signed InRelease/package indexes and pinned the public closure. Assembled the
  builder with networking disabled, exported/reloaded it, verified all saved
  layer diff IDs and recorded immutable image/archive identities.
- Real C and C++ ARM smoke compilation passed under shared FW-008 flags:
  GCC 4.8.3, ARM ELF32/EABI5/hard float, expected loader, nproc=6,
  MAKEFLAGS=-j6, 8 GiB memory, zero container swap and only loopback networking.
  Required C/C++ symbol-version sets are provided by the reconstructed stock
  libraries. This is static ABI evidence; no camera executable was run.
- Re-fetched the original maintainer recovery attachment and matched the
  retained bytes. Reconstructed/validated both filesystems and prepared
  deterministic candidate tgz inputs, independently rereading every payload,
  permission, owner, timestamp and symlink. Both home version files match the
  required base. These are maintainer equivalent rebuilds, not device dumps or
  vendor-signed originals; private input approval must cover that distinction.
- Downloaded the official 0.5.8 y203c archive and matched its publisher asset
  digest. The semantic validator passes against both real official JFFS2 images,
  including base/hack versions and model. No new firmware exists to compare.
- Final Linux regressions: 32 passed, zero skips. Windows host guards: 28 passed.
  Shell syntax checks passed. Candidate-size ceilings remain documented upstream
  examples; no new camera partition measurement is claimed.

The complete candidate lock has 19 input files and
108 additional provenance records; every
input SHA-256 was rechecked. Its review_status remains UNREVIEWED and no
approved lock is manufactured. The private lock digest is
`5c630babf0398b840e3dde53f416cc14a85b599936c3bdf85138d58a826fb051`.
The prospective execution-lock digest, after changing only review_status to
approved following explicit approval, is
`a8811138136127fd3cf763ac30ec0dc9c7741e5b6122f36f5bb0e6a0228662c1`. No approved execution lock has
been written. These exact bytes and the final checkout revision must be reviewed.
The acceptance criteria explicitly require a complete **approved** private lock,
and FW-008 requires an independently reviewed entrypoint revision. No PR reviews
were present when checked. Therefore private preflight and compilation were not
attempted with self-approved hashes or approval tokens.

Source revision: `c8582405b2c3c0e3b80219b0e71e21785a482867`.
Tested entrypoint code revision: `f0e7262d0bf36353fbd04996377299de35bc4071`.
Workflow revision: `5a05439df718e2d1d7b93f9cf5a0fdfe7c9a2306`.
The executable runner's approval must name the final checkout HEAD (including
this report commit), not merely the earlier code commit.

Builder assembly and acquisition timings/peaks were not comprehensively sampled;
the ARM smoke has its own measured duration in the JSON evidence. No elapsed or
peak resource measurement is presented as a firmware-build result. All large
inputs, the builder, native Docker storage, source checkout, logs and staging
remain on the selected data disk. No broad cache pruning, shared WSL config
change, Docker service change, camera access, flashing or merge occurred.

See [minimum dependencies and provenance](fw-001-minimum-dependencies.md),
[machine-readable continuation evidence](fw-001-minimum-input-evidence.json),
[static audit](fw-001-dependency-audit.json) and
[Git archive verification](fw-001-public-git-archive-evidence.json).

Publication used the connected GitHub Git-object API after the native push
required interactive credentials. All uploaded blob identities and all three
incremental commit trees match the tested local objects exactly. The original
local commits are preserved in a task backup ref; the public code revision above
has the same tree as the tested local code revision recorded in the JSON evidence.


## Approved execution and runtime fixes (2026-11-27)

The owner explicitly approved entrypoint `f8aa2d06e3172a085f59c3236d5473c1c7fe680b`
and execution lock `a8811138136127fd3cf763ac30ec0dc9c7741e5b6122f36f5bb0e6a0228662c1`.
The first actual private preflight passed. The first build stopped because
Debian installs mkfs.jffs2 in /usr/sbin, outside the reviewed compiler PATH.
The owner then approved execution lock
`15bfcc1a2bea6e1ec502bc37c895bf9f2d83f14d11221d0f5c276b89178d47e8`.
Its builder is `sha256:05a7092f12531a7ed9b349313db26deb29b2e9af9a43b28e16de9b55063a3119`;
archive SHA-256 `809b1efe6c0c5cfef8279d77901affe1e4c493dc831dfb36f258afb61f1cc796`.
The only additional image layer contains the mkfs.jffs2 symlink; the original
eight layers and other 18 input files are unchanged. All required tools and a
real packer/semantic filesystem fixture passed. No new package/source was added.
The approved stock-equivalence, mdnsd historical-content and Linaro-signature
limitations remain applicable.

Actual pristine-source compilation exposed these runtime issues:

- Global MAKEFLAGS=-j6 triggers the unordered live555 library prerequisite in
  the pinned rRTSPServer Makefile. Serial compilation preserves the original
  source and its intended dependency order. Container CPU quota/affinity remain
  independently configurable; the updated wrapper uses one compiler job.
- A subsequent serial attempt reached rRTSPServer but Autoconf rejected newly
  created files 8–9 seconds in the future. New WSL connections also failed with
  E_UNEXPECTED. The owner explicitly approved one WslService restart; standard
  Windows UAC elevation performed it. Docker Desktop was stopped. No shared
  configuration or protection policy was changed. New connections recovered.
- The next PowerShell invocation compiled rRTSPServer, rtsp_server_yi and
  sftp-server, then stopped in snapshot. FFmpeg configure could not execute
  host sanity tests in the default noexec /tmp. The updated wrapper sets
  TMPDIR=/work/tmp; the /tmp protections are retained.

No firmware artifact was accepted from these failed attempts. Source and all
nine recursive gitlinks passed the actual container checks. No external vendor
SDK component was needed by the compilation reached so far.

| Actual attempt | Verify/cache seconds | Preflight seconds | Primary stage seconds | Total seconds |
| --- | ---: | ---: | ---: | ---: |
| Missing packer PATH | 25.026 | 1.543 | 184.087 | 211.932 |
| Parallel prerequisite race | 22.533 | 1.572 | 477.822 | 507.217 |
| Autoconf clock check | 16.062 | 1.473 | 658.312 | 677.13 |
| FFmpeg noexec TMPDIR | 23.965 | 3.472 | 916.908 | 947.969 |

Stage times include verified staging, Docker load and cleanup. Every invocation
rehashed all 19 local files; each downloaded zero bytes. These failed timings
are not successful firmware build or reproducibility results.

The production cache routine was also exercised with the actual approved bytes:
four private local files, 15 digest-verified public cache hits, zero downloaded
bytes. A corrupted disposable stock copy and a changed independently pinned
public digest were rejected. Only task-owned test copies were removed.
Elapsed time: 112.663 seconds. Approved inputs were preserved.

The corrected TMPDIR was independently tested with the approved public FFmpeg
source and the same original GCC 4.8.3 builder. Full configure and compilation
of libavcodec/libavutil passed in 138.329 seconds, at six CPUs/8 GiB, no network,
readonly root and retained /tmp noexec. No stock input or ARM execution was used;
the probe's compiled outputs are not reused by firmware builds.

The follow-up runner also adds uniquely labelled, automatic actual-container
resource/isolation observations, preserves primary observations in its verified
checkpoint, checks the pinned official reference and ARM dependency/version
sets, and explains repeat differences only when they reduce to filesystem
mtimes, ELF compile timestamps and derived build IDs. Other differences block
success. It no longer substitutes an unconditional post-build blocked marker
for these checks. Full firmware acceptance remains pending actual successful
primary/repeat outputs and their validation under the reviewed follow-up.


Follow-up public validation: **38 tests passed, zero skips** inside the actual
minimal builder, including the reproduced unordered-make prerequisite fixture.
Windows: 25 tests passed with one GNU-make fixture skipped because Windows has
no GNU make; all 28 host guards passed. The native distro also lacks GNU make;
the builder run supplies the complete Linux execution evidence. Shell and
PowerShell syntax checks passed. Firmware source, stock inputs and VERSION
remain unchanged.

The corrected automatic observer passed an actual public container test at
6 CPU quota/affinity, 8 GiB RAM, zero swap, readonly root/inputs, capabilities
0xb, seccomp, no-new-privileges and loopback-only networking. The compiler nproc
guard returned 1; native docker-exec nproc returned 6, and these are recorded
separately. Its initial observation used docker-exec's base PATH rather than the
compiler guard and was corrected before any private follow-up execution.
Five samples observed 546.95% CPU and 34,152,120 bytes RAM during a deliberate
public six-worker load; these are not firmware resource peaks. The run took
37.746 seconds, downloaded zero bytes and verified both executable /work/tmp
and retained noexec /tmp behavior.

The complete artifact validator also passed against two disposable copies of
the independently verified official images in 2.277 seconds: no differences,
no missing required hack ELF files. This is a public reference fixture, not a
new firmware build or independent repeat. Actual firmware validation remains
pending. Independent review of the published follow-up entrypoint is required
before the private build gate accepts its new revision; the approved lock and
all 19 input bytes remain unchanged.


## Independent P1/P2 review and remediation (2026-11-27)

Reviewed PR #3 at `af4abae998bbb0efce5294c96007854e4786fa87`.
The five requested findings were confirmed in the runner, artifact validator and
execution documentation. Changes are confined to CI/build tooling, regression
tests and documentation; the upstream firmware source, approved builder image,
lock, private inputs, public dependencies and cache locations are unchanged.

| Finding | Remediation |
| --- | --- |
| P1 ARM ABI and library paths | Require ELF32 little-endian ARM EABI5 hard-float, loadable segments and matching loader-backed dynamic/version tables; verify the target interpreter, selected library provider, image-local symlinks and transitive dependencies. Do not union versions from unrelated files sharing a basename. |
| P1 official equivalence | Gate primary and repeat individually against the verified official 0.5.8 image trees, including path, mode, uid/gid and file content; report and reject unexplained differences even when the two new builds agree. |
| P1 checkpoint evidence | Revalidate output bytes, metadata digest, builder/observation identity, exactly one complete sampled container observation and current approved limits before reuse. Missing or inconsistent evidence invalidates the checkpoint. |
| P2 normalization | Only a structurally valid GNU build-id descriptor can be masked; arbitrary timestamp-like bytes are not normalized. File mode/type and other content changes remain visible. |
| P2 execution status | Update approved-input/preflight history, checkpoint behavior, remaining acceptance gates and report status. A blocked artifact validator leaves the corresponding stage BLOCKED. Diagnostic-only validation is UNVERIFIED/nonzero. |

Focused local Linux tests (not firmware compilation): 6 artifact-validator tests,
3 resource-observer tests and 1 isolated checkpoint regression method passed
(10 total, zero failures/skips). The artifact and observer modules and their
complete focused test files were reconstructed from the prepared Git blobs and
verified by Git blob SHA. The artifact tests use synthetic ELF fixtures and
mocked filesystem inspection; the checkpoint test uses the copied runner
checkpoint/output/atomic-write functions with a minimal FW-008 import stand-in
and real temporary archives/hash checks. Cases include wrong architecture/flags,
missing interpreter, decoy dynamic tables, basename shadowing, path restriction,
symlink loops, missing transitive libraries, arbitrary timestamp changes,
non-equivalent repeat/official contents and invalid checkpoint observations.

A full native checkout was unavailable (GitHub DNS failed in the test runtime),
so the entire FW-001/FW-008 test suite, PowerShell host tests, actual builder
runtime, and the official-release fixture under the stricter validator were not
run in this review. Prior successful test counts above describe the prior code,
not this review revision. Full suite execution remains a local verification step.
No complete firmware compilation, second build, camera execution or flash was
attempted. The strict policy may identify legitimate historical toolchain or
compression metadata differences; they are intentionally not auto-approved.
The static path model does not prove actual runtime loader state, SD-card
contents or dynamically loaded modules; inherited DT_RPATH is blocked pending
proof. Checkpoint validation is local consistency checking, not a signature or
attestation against arbitrary rewriting of the trusted local staging directory.

Approved execution lock remains
`15bfcc1a2bea6e1ec502bc37c895bf9f2d83f14d11221d0f5c276b89178d47e8`.
The next run needs explicit approval of the new final HEAD. Continue with the
existing inputs-v2/lock-v2.json, dedicated distro and six CPUs/eight GiB; do not
clear caches. Revision-specific checkpoints cannot cross the new entrypoint SHA;
mid-compile resume is not supported. All verified dependencies are retained.
FW-001 remains incomplete until actual primary/repeat builds and artifact gates
pass. This review does not approve release, flashing or merging PR #3.
