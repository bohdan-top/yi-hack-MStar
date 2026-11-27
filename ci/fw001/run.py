#!/usr/bin/env python3
"""FW-001 orchestration; FW-008 remains the sole firmware build entrypoint."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
import image_filesystem

if sys.platform.startswith("linux"):
    import fcntl
    import resource
else:
    fcntl = resource = None

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "ci/fw008/manual-build.py"
spec = importlib.util.spec_from_file_location("fw008", ENTRY)
fw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw)
image_spec = importlib.util.spec_from_file_location("image_structure", Path(__file__).with_name("image_structure.py"))
image_structure = importlib.util.module_from_spec(image_spec)
image_spec.loader.exec_module(image_structure)
NAMES = ("home_y203c", "sys_y203c", "y203c_0.5.8.tgz")
GIB = 1024 ** 3


def require(ok, message):
    fw.require(ok, message)


def call(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()


def atomic_json(path, data):
    # Atomic replacement on the same filesystem. Never publish private logs.
    fd, name = tempfile.mkstemp(prefix=".fw001-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(data, out, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def disk_check(paths, budget):
    for p in paths:
        require(shutil.disk_usage(p).free >= budget, "Insufficient free disk space")


def safe_file(path, root):
    return (path.is_file() and not path.is_symlink()
            and path.resolve() == root.resolve() / path.relative_to(root))


def verify_outputs(folder, key):
    """Recheck outputs and metadata, not a success marker alone."""
    require(folder.is_dir() and not folder.is_symlink(), "Invalid output directory")
    meta = folder / "metadata.json"
    require(safe_file(meta, folder), "Missing build metadata")
    data = json.loads(meta.read_text())
    require(data["target"] == "y203c" and data["source_sha"] == fw.BASE
            and data["entrypoint_sha"] == key["entrypoint"]
            and data["lock_sha256"] == key["lock"]
            and data["builder_image"] == key["image"]
            and data["requested_cpus"] == key["cpus"]
            and data["requested_memory_gib"] == key["memory_gib"]
            and data["release_approved"] is False, "Output provenance mismatch")
    hashes = {}
    for name in NAMES:
        path = folder / name
        require(safe_file(path, folder) and path.stat().st_size > 0, "Missing output")
        hashes[name] = fw.digest(path)
    require(hashes == data["output_sha256"], "Output digest mismatch")
    with tarfile.open(folder / NAMES[2], "r:gz") as archive:
        members = archive.getmembers()
        require(len(members) == 2 and {m.name for m in members} == set(NAMES[:2])
                and all(m.isfile() for m in members), "Unexpected archive members")
        for member in members:
            with archive.extractfile(member) as stream:
                require(hashlib.file_digest(stream, "sha256").hexdigest() == hashes[member.name],
                        "Archive content mismatch")
    return hashes


def resume_primary(checkpoint, output_root, key, report):
    """A checkpoint never substitutes for provenance and byte verification."""
    if not checkpoint.is_file() or checkpoint.is_symlink():
        return None
    try:
        saved = json.loads(checkpoint.read_text())
        name = saved["directory"]
        require(saved["key"] == key and isinstance(name, str) and name.startswith("primary-")
                and Path(name).name == name, "Checkpoint key/path mismatch")
        out = output_root / name
        hashes = verify_outputs(out, key)
        require(hashes == saved["hashes"], "Checkpoint digest mismatch")
        report["primary_resumed"] = True
        return out, hashes
    except (fw.Blocked, OSError, ValueError, TypeError, KeyError, tarfile.TarError):
        report["checkpoint_invalidated"] = True
    return None


def approved_download(entry, dest, budget, paths, stats):
    # Only the reviewed baseline public inventory may supply network URLs.
    inv = {x["path"]: x for x in fw.read_inventory()["files"]}
    candidate = inv.get(entry["path"], {})
    require(entry["path"].startswith("src/") and entry["source"] == candidate.get("source")
            and entry["version"] == candidate.get("version")
            and urllib.parse.urlsplit(entry["source"]).scheme == "https",
            "Missing/tampered private input or non-inventoried URL; restore approved input")
    if candidate.get("sha256"):
        require(entry["sha256"] == candidate["sha256"], "Public digest differs from inventory")
    disk_check(paths, budget)
    fd, temporary = tempfile.mkstemp(prefix=".download-", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            with urllib.request.urlopen(entry["source"], timeout=60) as response:
                require(urllib.parse.urlsplit(response.geturl()).scheme == "https",
                        "Insecure redirect")
                while chunk := response.read(1024 * 1024):
                    disk_check(paths, budget)
                    output.write(chunk)
                    stats["downloaded_bytes"] += len(chunk)
        require(fw.digest(Path(temporary)) == entry["sha256"], "Downloaded digest mismatch")
        os.replace(temporary, dest)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare_inputs(lock, source, inputs, cache, snapshot, budget, paths, stats):
    for entry in fw.validate_lock(lock, source):
        name = entry["path"]
        original = inputs / name
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        disk_check(paths, budget)
        if safe_file(original, inputs) and fw.digest(original) == entry["sha256"]:
            selected = original
            stats["verified_local_inputs"] += 1
        else:
            # Private archives, SDK/builder and source bundle cannot be downloaded here.
            require(name.startswith("src/"), "Missing/tampered private input: " + name)
            selected = cache / entry["sha256"]
            if safe_file(selected, cache) and fw.digest(selected) == entry["sha256"]:
                stats["verified_cache_hits"] += 1
            else:
                approved_download(entry, selected, budget, paths, stats)
        shutil.copyfile(selected, target)
        require(fw.digest(target) == entry["sha256"], "Snapshot digest mismatch")


def run(args, report):
    require(sys.platform.startswith("linux"), "WSL2 Linux required")
    require(fw.SHA.fullmatch(args.approved_entrypoint) and
            fw.DIGEST.fullmatch(args.approved_lock_sha256), "Explicit approvals required")
    actual = call("git", "-C", str(ROOT), "rev-parse", "HEAD")
    require(actual == args.approved_entrypoint, "Unapproved entrypoint revision")
    require(not call("git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all",
                     "--ignored", "--", "ci/fw008", "ci/fw001", "scripts/run-fw001.ps1"),
            "Build entrypoint files must be pristine")
    require(1 <= args.cpus <= len(os.sched_getaffinity(0)) and args.memory_gib >= 1,
            "Requested resource limits unavailable")
    raw = args.lock.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == args.approved_lock_sha256, "Lock digest mismatch")
    lock = json.loads(raw)
    fw.validate_lock(lock, fw.BASE)
    require(all(not p.resolve().is_relative_to(ROOT) for p in
                (args.inputs, args.lock, args.output_root, args.report_dir, args.stage_root)),
            "Private files must be outside repository")
    require(not os.environ.get("DOCKER_HOST") and not os.environ.get("DOCKER_CONTEXT"),
            "Unset Docker host/context overrides")
    require(call("docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}")
            == "unix:///var/run/docker.sock", "Native local Docker socket required")
    # Reject Docker Desktop/remote data roots: dedicated native dockerd in this distro.
    require(bool(call("pgrep", "-x", "dockerd")), "Native dockerd is not running")
    rootdev = Path("/").stat().st_dev
    require(call("findmnt", "-n", "-o", "FSTYPE", "/") == "ext4", "Use dedicated ext4 distro")
    docker_root = Path(call("docker", "info", "--format", "{{.DockerRootDir}}"))
    require(docker_root.is_absolute() and docker_root.is_dir() and
            docker_root.stat().st_dev == rootdev, "Docker data must be on dedicated distro ext4")
    args.stage_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not args.stage_root.is_symlink() and args.stage_root.stat().st_dev == rootdev
            and args.stage_root.stat().st_uid == os.getuid()
            and not (args.stage_root.stat().st_mode & 0o077),
            "Staging must be a private owner-only directory on dedicated distro ext4")
    # All library/subprocess temporary files must use the validated ext4 staging root.
    os.environ["TMPDIR"] = str(args.stage_root)
    tempfile.tempdir = str(args.stage_root)
    args.output_root.mkdir(parents=True, exist_ok=True)
    cache = args.stage_root / "verified-downloads"
    cache.mkdir(mode=0o700, exist_ok=True)
    require(not cache.is_symlink() and cache.stat().st_uid == os.getuid()
            and not (cache.stat().st_mode & 0o077), "Unsafe cache directory")
    budget = args.min_free_gib * GIB
    volumes = (args.stage_root, args.output_root, args.inputs)
    report["disk_free_before_bytes"] = [shutil.disk_usage(p).free for p in volumes]
    report["disk_scope"] = "distro ext4, output volume, input volume; may overlap"
    report["environment"] = {"python": sys.version.split()[0],
                             "docker": call("docker", "version", "--format", "{{.Server.Version}}")}
    key = {"entrypoint": actual, "source": fw.BASE, "lock": args.approved_lock_sha256,
           "image": lock["image_id"], "cpus": args.cpus, "memory_gib": args.memory_gib}
    report["revisions"] = {"source": fw.BASE, "entrypoint": actual, "workflow": None}
    key_id = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
    checkpoint = args.stage_root / ("checkpoint-" + key_id + ".json")
    stages = report["stages"]

    def stage(name, fn):
        print("[FW-001] " + name, flush=True)
        start = time.monotonic()
        row = {"name": name, "status": "BLOCKED"}
        stages.append(row)
        try:
            disk_check(volumes, budget)
            result = fn()
            row["status"] = "PASS"
            return result
        finally:
            row["elapsed_seconds"] = round(time.monotonic() - start, 3)

    # Advisory lock protects local checkpoints/cache from concurrent runner instances.
    mutex = args.stage_root / "runner.lock"
    with mutex.open("a") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix="fw001-snapshot-", dir=args.stage_root) as tmp:
            snapshot = Path(tmp)
            stage("verify/cache inputs", lambda: prepare_inputs(
                lock, fw.BASE, args.inputs, cache, snapshot, budget, volumes, report))
            shared = [sys.executable, "-B", str(ENTRY), "--inputs", str(snapshot),
                      "--lock", str(args.lock), "--approved-lock-sha256", args.approved_lock_sha256,
                      "--approved-entrypoint", actual, "--temp-root", str(args.stage_root),
                      "--cpus", str(args.cpus), "--memory-gib", str(args.memory_gib)]
            stage("FW-008 private preflight", lambda: subprocess.run(
                shared + ["--mode", "preflight"], check=True))
            if args.preflight_only:
                report["status"] = "PREFLIGHT PASS; full build NOT RUN"
                return 0

            def new_build(label):
                out = args.output_root / (label + "-" + uuid.uuid4().hex)
                subprocess.run(shared + ["--mode", "full", "--output", str(out)], check=True)
                return out, verify_outputs(out, key)

            first = None if args.clean else resume_primary(
                checkpoint, args.output_root, key, report)
            if first is None:
                first = stage("primary offline build", lambda: new_build("primary"))
            report["primary_image_structure"] = stage("primary JFFS2 structural validation",
                lambda: image_filesystem.inspect_firmware_pair(first[0]))
            if not report["primary_resumed"]:
                atomic_json(checkpoint, {"key": key, "directory": first[0].name, "hashes": first[1]})
            # Always a new output directory and fresh FW-008 temp workspace.
            # No repeat checkpoint, compiled output, or shared writable build cache.
            second = stage("independent offline repeat build", lambda: new_build("repeat"))
            report["repeat_image_structure"] = stage("repeat JFFS2 structural validation",
                lambda: image_filesystem.inspect_firmware_pair(second[0]))
            report["artifact_sha256"] = {"primary": first[1], "repeat": second[1]}
            report["artifact_hash_matches"] = {n: first[1][n] == second[1][n] for n in NAMES}
            report["artifact_content_matches"] = {n: report["primary_image_structure"][n]["content_manifest_sha256"] ==
                report["repeat_image_structure"][n]["content_manifest_sha256"] for n in image_structure.CANDIDATE_LIMITS}
            report["status"] = "BUILD OUTPUTS VERIFIED; full FW-001 acceptance BLOCKED"
            # Until trusted partition limits, JFFS2 integrity, release comparison, ARM
            # ABI and actual isolation evidence are available, never return full success.
            report["remaining_validation"] = [
                "confirmed hardware partition limits (current ceilings are documented candidate values)",
                "comparison against independently verified official release",
                "ARM smoke test and SDK/license provenance evidence",
                "actual network isolation and effective resource-limit evidence",
                "explanation of any nondeterministic output differences"]
            return 2


def main():
    parser = argparse.ArgumentParser()
    for p in ("inputs", "lock", "output-root", "report-dir", "stage-root"):
        parser.add_argument("--" + p, type=Path, required=True)
    for p in ("approved-entrypoint", "approved-lock-sha256"):
        parser.add_argument("--" + p, required=True)
    parser.add_argument("--cpus", type=int, default=6)
    parser.add_argument("--memory-gib", type=int, default=8)
    parser.add_argument("--min-free-gib", type=int, default=40)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    report = {"status": "BLOCKED", "stages": [], "requested_cpus": args.cpus,
              "requested_memory_gib": args.memory_gib, "verified_local_inputs": 0,
              "verified_cache_hits": 0, "downloaded_bytes": 0, "primary_resumed": False,
              "checkpoint_invalidated": False, "release_approved": False,
              "peak_container_cpu_ram": "not measured", "peak_temp_storage": "not measured"}
    started = time.monotonic()
    rc = 1
    # Require report destination outside checkout before writing anything.
    require(args.min_free_gib > 0 and not args.report_dir.resolve().is_relative_to(ROOT),
            "Invalid disk budget or report path")
    args.report_dir.mkdir(parents=True, exist_ok=True)
    try:
        rc = run(args, report)
    except (fw.Blocked, OSError, ValueError, KeyError, TypeError, tarfile.TarError,
            subprocess.CalledProcessError) as error:
        # Do not persist exception strings (may contain private paths/URLs).
        report["failure_type"] = type(error).__name__
        print("BLOCKED: inspect local prerequisites and private logs; see FW-001 documentation",
              file=sys.stderr)
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if resource is not None:
            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            report["client_children_cpu_seconds"] = usage.ru_utime + usage.ru_stime
            report["client_children_max_rss_kib"] = usage.ru_maxrss
        report["resource_scope"] = "Linux child processes only; excludes Docker daemon/container"
        if "disk_free_before_bytes" in report:
            report["disk_free_after_bytes"] = [shutil.disk_usage(p).free for p in
                (args.stage_root, args.output_root, args.inputs)]
        atomic_json(args.report_dir / ("fw001-" + uuid.uuid4().hex + ".json"), report)
    return rc


if __name__ == "__main__":
    sys.exit(main())
