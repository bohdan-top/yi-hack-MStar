# FW-001 — Windows local baseline runner (full build acceptance pending)

## Preconditions

Use a dedicated WSL2 distro named FirmwareBuild (or specify -Distro) registered on the selected non-system drive, with ext4.vhdx on that drive and a native Linux Docker daemon whose data root is on the same ext4 filesystem. Do not use Docker Desktop's shared daemon or a remote context. Provision the distro, Docker, Python 3.11+, Git, procps and util-linux using approved versions before running. No installation, global WSL configuration, existing distro migration or Docker service changes are automated. The host runner reads .wslconfig before launching Linux and requires swap=0 or an explicit swapFile beneath DataRoot. It never edits this shared configuration or restarts WSL. A configuration file alone does not prove the running VM has applied it; effective swap placement still needs verification before compilation. Changes and any required shared VM restart need owner approval. The Windows data drive should have at least 40 GiB free (configurable); ext4 and Windows input/output free space are checked too. Allow for staging copies and two independent output sets. No GPU is required.

Follow [FW-008 input preparation](fw-008-manual-build.md). Obtain the licensed compatible ARM GCC 4.8.3 toolchain and matching sysroot, pinned builder archive, pristine source.tar with recursive submodules, and stock tgz files independently. Audit the baseline dependencies and obtain additional vendor SDK components only if a concrete requirement is demonstrated. A complete MSC3XX SDK is not a mandatory prerequisite; all actually used components still require provenance, licensing and compatibility verification. Resolve the missing archive digests and review the lock. Never approve hashes merely because a download matches itself. Keep all private material on the data drive, outside Git. An independently reviewed lock digest and reviewed entrypoint commit are mandatory. Review this PR before giving it private inputs.

## Windows command

From the reviewed branch checkout in PowerShell:

```powershell
.\scripts\run-fw001.ps1 -DataRoot "E:\FirmwareBuild" -CpuLimit 6 -MemoryGB 8 -ApprovedLockSha256 REVIEWED_64_HEX -ApprovedEntrypoint REVIEWED_40_HEX -PreflightOnly
```

Remove -PreflightOnly to attempt the full build and repeat. The default data paths are inputs, lock.json, outputs, reports and Windows temp under DataRoot. All configurable private Windows paths, the distro VHD and configured swap file must remain beneath DataRoot; relative paths, UNC/device paths and reparse-point ancestors are rejected. Windows TEMP/TMP/TMPDIR are restored after execution. Python and subprocess temporary files use the validated Linux staging root. Override -Inputs, -LockFile, -OutputRoot, -Distro, -LinuxStageRoot and -MinimumFreeGB as needed. Staging/cache/checkpoints live on the distro's ext4 filesystem (physically on the data disk); the default Linux staging root is /var/tmp/fw001. The distro user must own the private staging directory. The approved lock SHA is not generated automatically. The Windows report and Linux report are separate sanitized JSON files. Private build logs remain in each output directory. WSL output and detailed host exceptions go to private-prefixed logs beneath reports; never commit those logs. Console and host JSON failures contain a stable reason code instead of arbitrary exception text.

## Resume and limits

The runner revalidates the lock and every input on each invocation, including SHA-256 of cache hits. Missing or corrupted public dependencies can be downloaded into the digest-addressed cache only from the approved baseline inventory with reviewed digests. Missing private archives stop execution. No private input is overwritten. The primary successful build checkpoint includes source/entrypoint, lock digest, builder image and requested resource limits; output metadata digest, hashes and archive members are rechecked before reuse, together with exactly one complete saved isolation/resource observation matching the build metadata observation ID, builder identity and approved limits. Missing, malformed or mismatched evidence invalidates the checkpoint. A changed key (including entrypoint revision) triggers a new build without deleting the retained output or the digest-addressed input cache. -Clean ignores a prior checkpoint without deleting retained files. The independent repeat always uses a new output and FW-008 workspace, and never resumes compiled outputs. Mid-compile resume is not supported. Temporary task-owned snapshot/staging directories are removed on normal process unwinding; retained logs, outputs and cache are not pruned. Abrupt termination can leave orphaned private temporary directories.

Docker receives explicit CPU affinity, CPU quota, RAM and memory+swap limits. MAKEFLAGS and common make/nproc overrides are bounded in the shared build wrapper; unusual invocations and actual cgroup enforcement still need runtime validation. These are container limits, not global WSL VM limits. The ARM compiler version and ELF header/ABI smoke checks run inside the limited container before firmware compilation. Device ABI compatibility remains subject to validation. FW-008 continues to enforce offline isolation, verified inputs and source checks.

## Evidence and remaining gates

Preflight-only exit 0 means input preflight only. A full build producing two sets of valid update archives still returns nonzero until FW-001 validation is complete. JFFS2 integrity, partition limits, model/version, official-release comparison, actual isolation, peak container resource use and reproducibility analysis are implemented gates; successful real primary and repeat builds and their passing evidence remain pending. The report records requested limits, observed stage elapsed time, disk free-space snapshots, child-process CPU/RSS (excludes Docker), bytes downloaded and cache/resume outcomes; unavailable measurements are explicit. Reports now include both output hash sets when builds execute. No firmware hashes are available until a real build succeeds. Do not commit raw logs, private manifests or build outputs.

Run these synthetic tests in trusted Linux before private execution (Windows host-side execution does not replace Linux/container verification):

```sh
python3 -B -m unittest discover -s ci/fw008 -p 'test_*.py'
python3 -B -m unittest discover -s ci/fw001 -p 'test_*.py'
bash -n ci/fw008/build-offline.sh
```

On Windows, run host checks without Pester and run the portable unit tests with installed Python 3.11+. Use a task-owned test directory on the data disk:

```powershell
$env:TEMP = 'E:\FirmwareBuild\temp'
$env:TMP = $env:TEMP
$env:FW008_TEST_BASH = 'C:\Program Files\Git\bin\bash.exe'
.\ci\fw001\test-host.ps1 -TestRoot $env:TEMP
python -B -m unittest discover -s ci/fw001 -p 'test_*.py'
python -B -m unittest discover -s ci/fw008 -p 'test_*.py'
```

Git Bash is used only for shell guard tests and syntax checks. It does not run firmware compilation. Two symlink fixture tests are explicitly skipped on Windows; the output-archive test still checks members and bytes there. On Linux the full symlink checks execute. Infrastructure shell files have LF enforced by .gitattributes; prepare source.tar from a pristine Linux checkout with Linux modes and LF source bytes, not a Windows checkout converted by core.autocrlf. Only CI shell scripts are normalized by this PR; upstream firmware files are untouched.

Historical inventory blockers have been superseded: all 19 input files (15 public module archives plus four private inputs) have an approved derived-builder lock; actual private preflight and production cache verification passed. An approved lock still cannot override an independently pinned baseline public digest. See the execution report for provenance limitations and observed cache results.

See [execution evidence](fw-001-execution-report.md). This is not release or flash approval.


## Executed dedicated environment probe

The dedicated FirmwareBuild distro/native Docker and shared swap placement were provisioned after explicit owner approval. See the current execution report and environment JSON for observed versions, hashes and measurements. The build runner still requires the separate approved private lock; environment probes never approve proprietary inputs or compile firmware.

A verified public Python runtime can exercise the actual FW-008 Docker arguments without the SDK. Run inside the dedicated distro, using an immutable, independently verified runtime ID:

```sh
python3 -B ci/fw001/probe-environment.py --image VERIFIED_SHA256_IMAGE_ID --stage-root /var/tmp/fw001 --report-dir /mnt/e/FirmwareBuild/reports --cpus 6 --memory-gib 8 --interrupt-after 2
python3 -B ci/fw001/probe-environment.py --image VERIFIED_SHA256_IMAGE_ID --stage-root /var/tmp/fw001 --report-dir /mnt/e/FirmwareBuild/reports --cpus 6 --memory-gib 8
```

The first invocation checks actual interruption cleanup; the second always uses a fresh workspace and checks cgroups, affinity, seccomp, no-new-privileges, capabilities, read-only mounts, network denial, download rejection and nproc/make environment. Sampled CPU/RAM observations describe this probe only. It does not test the 8 GiB OOM threshold, ARM GCC, upstream compilation, firmware checkpoints or artifact acceptance. No broad Docker/cache cleanup is performed.

On Docker 29 with the containerd store, runtime image identity can be a manifest digest rather than the registry's image-config digest. Verify the imported manifest/config/layer graph against authenticated original contents before recording the runtime ID in a reviewed lock. Do not replace an expected digest with an observed value merely to proceed. The execution report records the public probe's verified graph; it is not approval of an SDK builder.


## Minimum-input continuation (2026-11-27)

See [minimum dependency audit and candidate provenance](fw-001-minimum-dependencies.md). All 15 public module archives now have verification evidence, including the two snapshot downloads omitted by the earlier inventory. Earlier counts and blockers above are historical. Private lock and entrypoint approval remain mandatory; no automatic approval is introduced. The semantic validator now decompresses supported JFFS2 payloads and checks model/base/hack versions for both build outputs, but actual compilation, repeat and release comparison are still pending.


## Runtime fixes after approved execution

Use the approved derived builder and its unchanged lock digest documented in the
latest execution report. Supply the exact independently reviewed runner commit.
The Windows invocation is one command:

```powershell
./scripts/run-fw001.ps1 -DataRoot E:\FirmwareBuild -Inputs E:\FirmwareBuild\inputs-v2 -LockFile E:\FirmwareBuild\lock-v2.json -CpuLimit 6 -MemoryGB 8 -ApprovedLockSha256 15bfcc1a2bea6e1ec502bc37c895bf9f2d83f14d11221d0f5c276b89178d47e8 -ApprovedEntrypoint REVIEWED_RUNNER_COMMIT
```

The container retains the requested CPU quota and affinity. Compilation is
serial because the pristine rRTSPServer makefile has unordered prerequisites;
MAKEFLAGS and the compiler nproc guard both return one job. This avoids source
patches. TMPDIR is /work/tmp for executable host configure tests; Docker /tmp
stays noexec. The official release archive defaults to the documented candidate
file under DataRoot and must match the independently verified publisher digest.
Use -OfficialReferenceArchive to select another local copy of the same bytes.

Full runs automatically observe only their uniquely labelled build containers.
Reports include sampled CPU/RAM maxima, workspace apparent bytes, effective
cgroups, affinity, capabilities/seccomp, readonly mounts, network denial and
download-guard rejection. Poll interval is two seconds plus Docker stats/du
latency; maxima are observations, not continuous hard peaks. Workspace figures
exclude input snapshots, Docker layers and host allocation. Child CPU/RSS
counters are reported separately and exclude the Docker processes.

After both clean builds, the runner verifies all JFFS2 payloads and identities,
documented size ceilings, archive hashes, installed ARM library/version needs,
the pinned official reference and normalized repeat contents. Both primary and repeat must independently match the reference under the same conservative comparison. Unexplained content, path, type, ownership or permission differences return nonzero. Bit reproducibility and hardware execution are
separate claims. Successful compilation does not approve release or flashing.
For read-only revalidation of retained outputs, -ValidateOnly additionally takes
-PrimaryOutput, -RepeatOutput and -ReferenceDirectory, all inside DataRoot.
It rechecks the approved lock, original build metadata, artifact bytes and the
official reference; it does not compile or reuse a repeat checkpoint.


## Independent review hardening (2026-11-27)

The static ABI gate requires ARM little-endian ELF32, EABI5 hard-float flags,
loadable segments, a valid target interpreter where applicable, and a consistent
loader-backed dynamic/version table. It resolves the installed /home mount and
library paths from the pinned startup script plus target standard/multiarch
locations, follows image-local symlinks, and checks the selected provider's
versions and transitive dependencies rather than unioning basename matches.
Unverified search paths and inherited DT_RPATH block acceptance; approved
DT_RUNPATH directories can include $ORIGIN. This is an intentionally static
model of the installed image, not proof of runtime linker state, dynamic dlopen,
SD-card content, hardware instruction compatibility or camera execution.

Only filesystem mtime differences and a structurally validated GNU build-id
descriptor are automatically explained; no generic date/time substitution or
archive-content exception is allowed. Legitimate compile-time strings or
compressed archive metadata differences must first be evidenced and reviewed.
Both new builds must independently match the digest-pinned official 0.5.8
reference under this policy. The official reference itself and actual outputs
have not yet been retested with the strengthened gate. Diagnostic-only
validation without approved build provenance cannot return an acceptance PASS.

The primary checkpoint records and revalidates the metadata hash and the
observation ID bound to one actual container's sampled isolation evidence.
This protects against missing, stale, malformed or inconsistent local evidence;
it is not a signed attestation against an attacker with write access to the
entire trusted local staging/output environment. A new runner SHA requires new
entrypoint approval. Old successful checkpoints are revision-specific and are
not reused; no verified input, lock, builder, cache or existing output is deleted.
Mid-compilation resume remains unsupported.

Before authorizing a new private run, execute the existing Linux FW-001/FW-008
unit-test commands above in the dedicated WSL distro. The review's focused
synthetic tests and limitations are recorded in the execution report. The
approved lock and existing one-command invocation are unchanged except for the
new approved runner HEAD. Do not use -Clean for normal cache-preserving runs.
