# FW-008 — manual build bootstrap

Target: y203c / 6FUS only. Baseline: `c8582405b2c3c0e3b80219b0e71e21785a482867`. This PR does not change upstream firmware, flash a camera or approve a release.

## Hosted public CI

After merging the dispatch definition into master, open Actions → FW-008 Manual firmware build → Run workflow. Select preflight and the default immutable source. No push/PR/scheduled build. The workflow runs bootstrap tests and syntax checks and retains only public diagnostics for seven days. Hosted full requests intentionally fail: no stock/SDK secrets are accepted. No self-hosted runner is exposed to fork PRs. Mirror the reviewed bootstrap on firmware/y203c after branch creation from the baseline; do not merge master into the firmware branch.

## Trusted local Linux / WSL2

Use a dedicated machine/VM, local Docker daemon, Python 3.11+, Git, sufficient free disk; no camera/device mounts. Review the exact checkout and entrypoint commit, ensure clean checkout, and independently approve the immutable source commit and lock digest before handling private inputs. Do not run code from an unreviewed PR. Docker is not a hostile-code security boundary; use an isolated disposable VM, no other private data, no remote daemon or shared runner. Private inputs/output must be outside checkout.

Copy `ci/fw008/input-inventory.json` to a private lock file. It is **not an approved lock**. Fill every missing digest from trusted independent provenance, review the candidate immutable mdnsd commit (last master commit before the baseline commit date; exact historical dependency is unknown), record the origin/version of all additional inputs and nested Git dependencies; never bless hashes calculated only from an untrusted download. Set review_status to approved only after review. Obtain a licensed MStar MSC3XX SDK (not I1), ARM toolchain at /opt/yi/arm-linux-gnueabihf-4.8.3-201404, and build a reviewed amd64 Linux image with required host packages; pin all base images, SDK and package inputs in the private provenance record (additional_inputs: each entry must have source, version and SHA-256). Export the reviewed image as builder.tar using docker save; record its exact image ID and archive digest. Do not pull borodiliz/yi-hack by moving tag. No SDK or stock content goes to GitHub.

Prepare a clean detached Git checkout with recursive submodules at exact reviewed gitlinks (including .git metadata). Audit Git config/hooks/filters and archive contents before approving source.tar; no credentials in Git configuration. Archive checkout contents, not the enclosing directory. Private input directory layout mirrors the lock paths; stock inputs are trusted tgz filesystem archives (not JFFS2 raw images, to avoid privileged mtd access). Prefetch archives independently, including fallback provenance if chosen. Baseline requires primary BusyBox archive; alternate is inventoried but not automatically used. Missing paths/digests fail closed. For a reviewed fork revision, provide a separately approved complete manifest for that commit and its download inventory.

```sh
python3 ci/fw008/manual-build.py --mode preflight --lock /private/lock.json \
  --inputs /private/inputs --approved-lock-sha256 APPROVED_64_HEX --approved-entrypoint REVIEWED_40_HEX
python3 ci/fw008/manual-build.py --mode full --lock /private/lock.json \
  --inputs /private/inputs --approved-lock-sha256 APPROVED_64_HEX --approved-entrypoint REVIEWED_40_HEX \
  --output /private/new-build
```

Use --source EXACT_40_HEX for an independently approved fork revision. The supplied lock digest is an explicit local trust anchor, not an automated review mechanism. Staging copies only approved files into a fresh temp directory; digests are checked before loading/extraction. Source and recursive Git links are verified inside the container before compilation. Docker runs without network, privileged mode, device access or credentials; common download tools are denied with a marker checked at build phase boundaries. Raw logs and outputs stay private. The wrapper enables Bash errexit on the three top-level upstream phases (not a guarantee for every nested script). A successful compile must produce both nonempty images and exactly one update archive containing only the two regular images with matching sizes and SHA-256 digests; metadata contains source/entrypoint commits, input and output digests. Release acceptance is FW-001/FW-012.

## Known blockers / NOT VERIFIED

- Nine candidate public archive SHA-256 values with provenance are populated (publisher release metadata or distro manifests). All nine downloaded byte streams matched during the local FW-001 public audit; this does not approve the private lock. Four public digests, SDK/image and stock inputs still need provenance review. See docs/fw-001-execution-report.md for measured evidence. The checked-in inventory is deliberately not approved.
- Baseline mbedTLS filename mismatch is handled by a symlink to the real verified archive; mdnsd immutable ZIP root is similarly aliased to mdnsd-master. No tracked firmware files are modified. The metadata records the compatibility staging; the historical mdnsd contents and actual compile remain NOT VERIFIED.
- Nested dependency trees for mosquitto and mjpeg-avi could not be confirmed remotely; recursive local verification mandatory. Inventory includes direct upstream downloads and observed alternatives; transitive package/build-system provenance must be completed before approving lock.
- No real Docker build, output size/layout checks, reproducibility or hardware tests claimed. No workflow dispatch on default branch before merge.

## Test commands

```sh
python3 -B -m unittest discover -s ci/fw008 -p 'test_*.py'
bash -n ci/fw008/build-offline.sh
bash -n ci/fw008/download-guard.sh
python3 ci/fw008/manual-build.py --public --mode preflight
python3 ci/fw008/manual-build.py --public --mode full # expected nonzero
```

Synthetic fixtures exercise missing input, tamper, unapproved ref/lock, unsafe path, unpinned Git links and fresh staging. Synthetic output tests check archive integrity and reject symlinked output paths. Docker command flags are unit-tested, not a proof of isolation. The synthetic shell test also checks the download guard when upstream ignores wget failure. Actual container behavior must be demonstrated before FW-008 acceptance is closed.

See [executed bootstrap evidence](fw-008-bootstrap-evidence.md).

[Roadmap](firmware-roadmap.md) · [Task](../tasks/fw-008-manual-ci-build.md)
