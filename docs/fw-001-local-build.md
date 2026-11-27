# FW-001 — Windows local baseline runner (partial)

## Preconditions

Use a dedicated WSL2 distro named FirmwareBuild (or specify -Distro) registered on the selected non-system drive, with ext4.vhdx on that drive and a native Linux Docker daemon whose data root is on the same ext4 filesystem. Do not use Docker Desktop's shared daemon or a remote context. Provision the distro, Docker, Python 3.11+, Git, procps and util-linux using approved versions before running. No installation, global WSL configuration, existing distro migration or Docker service changes are automated. Review WSL swap placement separately: the runner cannot guarantee zero system-disk growth from WSL itself. The Windows data drive should have at least 40 GiB free (configurable); ext4 and Windows input/output free space are checked too. Allow for staging copies and two independent output sets. No GPU is required.

Follow [FW-008 input preparation](fw-008-manual-build.md). Obtain the licensed MSC3XX SDK, compatible ARM GCC 4.8.3 toolchain, pinned builder archive, pristine source.tar with recursive submodules, and stock tgz files independently. Resolve the missing archive digests and review the lock. Never approve hashes merely because a download matches itself. Keep all private material on the data drive, outside Git. An independently reviewed lock digest and reviewed entrypoint commit are mandatory. Review this PR before giving it private inputs.

## Windows command

From the reviewed branch checkout in PowerShell:

```powershell
.\scripts\run-fw001.ps1 -DataRoot "E:\FirmwareBuild" -CpuLimit 6 -MemoryGB 8 -ApprovedLockSha256 REVIEWED_64_HEX -ApprovedEntrypoint REVIEWED_40_HEX -PreflightOnly
```

Remove -PreflightOnly to attempt the full build and repeat. The default data paths are inputs, lock.json, outputs and reports under DataRoot. Override -Inputs, -LockFile, -OutputRoot, -Distro, -LinuxStageRoot and -MinimumFreeGB as needed. Staging/cache/checkpoints live on the distro's ext4 filesystem (physically on the data disk); the default Linux staging root is /var/tmp/fw001. The distro user must own the private staging directory. The approved lock SHA is not generated automatically. The Windows report and Linux report are separate sanitized JSON files. Private build logs remain in each output directory.

## Resume and limits

The runner revalidates the lock and every input on each invocation, including SHA-256 of cache hits. Missing or corrupted public dependencies can be downloaded into the digest-addressed cache only from the approved baseline inventory with reviewed digests. Missing private archives stop execution. No private input is overwritten. The primary successful build checkpoint includes source/entrypoint, lock digest, builder image and requested resource limits; output metadata, hashes and archive members are rechecked before reuse. A changed key triggers a new build. -Clean ignores a prior checkpoint without deleting retained files. The independent repeat always uses a new output and FW-008 workspace, and never resumes compiled outputs. Mid-compile resume is not supported. Temporary task-owned snapshot/staging directories are removed on normal process unwinding; retained logs, outputs and cache are not pruned. Abrupt termination can leave orphaned private temporary directories.

Docker receives explicit CPU affinity, CPU quota, RAM and memory+swap limits. MAKEFLAGS and common make/nproc overrides are bounded in the shared build wrapper; unusual invocations and actual cgroup enforcement still need runtime validation. These are container limits, not global WSL VM limits. The ARM compiler version and ELF header/ABI smoke checks run inside the limited container before firmware compilation. Device ABI compatibility remains subject to validation. FW-008 continues to enforce offline isolation, verified inputs and source checks.

## Evidence and remaining gates

Preflight-only exit 0 means input preflight only. A full build producing two sets of valid update archives still returns nonzero until FW-001 validation is complete. JFFS2 integrity, partition limits, model/version, official-release comparison, actual isolation, peak container resource use and reproducibility analysis remain pending. The report records requested limits, observed stage elapsed time, disk free-space snapshots, child-process CPU/RSS (excludes Docker), bytes downloaded and cache/resume outcomes; unavailable measurements are explicit. Do not commit raw logs, private manifests or build outputs.

Run these synthetic tests in trusted Linux before private execution:

```sh
python3 -B -m unittest discover -s ci/fw008 -p 'test_*.py'
python3 -B -m unittest discover -s ci/fw001 -p 'test_*.py'
bash -n ci/fw008/build-offline.sh
```

See [execution evidence](fw-001-execution-report.md). This is not release or flash approval.
