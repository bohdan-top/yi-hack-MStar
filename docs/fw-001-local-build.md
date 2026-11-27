# FW-001 — Windows local baseline runner (partial)

## Preconditions

Use a dedicated WSL2 distro named FirmwareBuild (or specify -Distro) registered on the selected non-system drive, with ext4.vhdx on that drive and a native Linux Docker daemon whose data root is on the same ext4 filesystem. Do not use Docker Desktop's shared daemon or a remote context. Provision the distro, Docker, Python 3.11+, Git, procps and util-linux using approved versions before running. No installation, global WSL configuration, existing distro migration or Docker service changes are automated. The host runner reads .wslconfig before launching Linux and requires swap=0 or an explicit swapFile beneath DataRoot. It never edits this shared configuration or restarts WSL. A configuration file alone does not prove the running VM has applied it; effective swap placement still needs verification before compilation. Changes and any required shared VM restart need owner approval. The Windows data drive should have at least 40 GiB free (configurable); ext4 and Windows input/output free space are checked too. Allow for staging copies and two independent output sets. No GPU is required.

Follow [FW-008 input preparation](fw-008-manual-build.md). Obtain the licensed MSC3XX SDK, compatible ARM GCC 4.8.3 toolchain, pinned builder archive, pristine source.tar with recursive submodules, and stock tgz files independently. Resolve the missing archive digests and review the lock. Never approve hashes merely because a download matches itself. Keep all private material on the data drive, outside Git. An independently reviewed lock digest and reviewed entrypoint commit are mandatory. Review this PR before giving it private inputs.

## Windows command

From the reviewed branch checkout in PowerShell:

```powershell
.\scripts\run-fw001.ps1 -DataRoot "E:\FirmwareBuild" -CpuLimit 6 -MemoryGB 8 -ApprovedLockSha256 REVIEWED_64_HEX -ApprovedEntrypoint REVIEWED_40_HEX -PreflightOnly
```

Remove -PreflightOnly to attempt the full build and repeat. The default data paths are inputs, lock.json, outputs, reports and Windows temp under DataRoot. All configurable private Windows paths, the distro VHD and configured swap file must remain beneath DataRoot; relative paths, UNC/device paths and reparse-point ancestors are rejected. Windows TEMP/TMP/TMPDIR are restored after execution. Python and subprocess temporary files use the validated Linux staging root. Override -Inputs, -LockFile, -OutputRoot, -Distro, -LinuxStageRoot and -MinimumFreeGB as needed. Staging/cache/checkpoints live on the distro's ext4 filesystem (physically on the data disk); the default Linux staging root is /var/tmp/fw001. The distro user must own the private staging directory. The approved lock SHA is not generated automatically. The Windows report and Linux report are separate sanitized JSON files. Private build logs remain in each output directory. WSL output and detailed host exceptions go to private-prefixed logs beneath reports; never commit those logs. Console and host JSON failures contain a stable reason code instead of arbitrary exception text.

## Resume and limits

The runner revalidates the lock and every input on each invocation, including SHA-256 of cache hits. Missing or corrupted public dependencies can be downloaded into the digest-addressed cache only from the approved baseline inventory with reviewed digests. Missing private archives stop execution. No private input is overwritten. The primary successful build checkpoint includes source/entrypoint, lock digest, builder image and requested resource limits; output metadata, hashes and archive members are rechecked before reuse. A changed key triggers a new build. -Clean ignores a prior checkpoint without deleting retained files. The independent repeat always uses a new output and FW-008 workspace, and never resumes compiled outputs. Mid-compile resume is not supported. Temporary task-owned snapshot/staging directories are removed on normal process unwinding; retained logs, outputs and cache are not pruned. Abrupt termination can leave orphaned private temporary directories.

Docker receives explicit CPU affinity, CPU quota, RAM and memory+swap limits. MAKEFLAGS and common make/nproc overrides are bounded in the shared build wrapper; unusual invocations and actual cgroup enforcement still need runtime validation. These are container limits, not global WSL VM limits. The ARM compiler version and ELF header/ABI smoke checks run inside the limited container before firmware compilation. Device ABI compatibility remains subject to validation. FW-008 continues to enforce offline isolation, verified inputs and source checks.

## Evidence and remaining gates

Preflight-only exit 0 means input preflight only. A full build producing two sets of valid update archives still returns nonzero until FW-001 validation is complete. JFFS2 integrity, partition limits, model/version, official-release comparison, actual isolation, peak container resource use and reproducibility analysis remain pending. The report records requested limits, observed stage elapsed time, disk free-space snapshots, child-process CPU/RSS (excludes Docker), bytes downloaded and cache/resume outcomes; unavailable measurements are explicit. Reports now include both output hash sets when builds execute. No firmware hashes are available until a real build succeeds. Do not commit raw logs, private manifests or build outputs.

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

The public inventory is still unapproved. Nine exact public archives have now been downloaded and checked against independently sourced candidate digests; four public digests and private prerequisites remain unresolved. An approved lock cannot override an independently pinned baseline public digest. Warm-cache results in the execution report cover the separate public provenance audit; production FW-001 cache/recovery checks are synthetic until approved inputs and native Docker are available.

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
