#!/usr/bin/env python3
"""FW-008: manual public preflight and trusted, offline local build."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "ci/fw008/input-inventory.json"
BASE = "c8582405b2c3c0e3b80219b0e71e21785a482867"
SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")


class Blocked(Exception):
    pass


def require(ok, message):
    if not ok:
        raise Blocked(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relative(value):
    p = PurePosixPath(value)
    require(value == p.as_posix() and not p.is_absolute() and
            bool(p.parts) and ".." not in p.parts and "." not in p.parts and
            all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in p.parts),
            "Unsafe input path")
    return p


def read_inventory():
    return json.loads(INVENTORY.read_text())


def validate_lock(lock, source):
    require(SHA.fullmatch(source), "Use an exact 40-character source commit")
    require(lock.get("schema") == 1 and lock.get("target") == "y203c" and
            lock.get("source_sha") == source, "Lock target/source mismatch")
    require(lock.get("review_status") == "approved", "Input lock is not approved")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", lock.get("image_id") or ""),
            "Missing reviewed builder image ID")
    require(isinstance(lock.get("submodules"), dict), "Missing recursive Git lock")
    for name, sha in lock["submodules"].items():
        relative(name)
        require(SHA.fullmatch(sha), "Unpinned submodule")
    provenance = lock.get("additional_inputs")
    require(isinstance(provenance, list) and bool(provenance),
            "Missing reviewed SDK, base image and host package provenance")
    for entry in provenance:
        require(bool(entry.get("source")) and bool(entry.get("version")) and
                "UNRESOLVED" not in entry["version"] and
                DIGEST.fullmatch(entry.get("sha256") or ""),
                "Unpinned builder dependency provenance")
    files = lock["files"]
    require(isinstance(files, list), "Missing input list")
    seen = set()
    for item in files:
        name = item["path"]
        relative(name)
        require(name not in seen, "Duplicate input")
        seen.add(name)
        require(DIGEST.fullmatch(item.get("sha256") or ""), "Missing SHA-256: " + name)
        require(bool(item.get("source")) and bool(item.get("version")) and
                "UNRESOLVED" not in item["version"], "Missing provenance: " + name)
        if name not in {"source.tar", "builder.tar",
                        "stock_firmware/y203c/home_y203c.tgz",
                        "stock_firmware/y203c/sys_y203c.tgz"}:
            require(name.startswith("src/") and name.endswith((".tar.gz", ".tar.bz2", ".tar.xz", ".zip")),
                    "Only explicit module archives are accepted")
    required = {"source.tar", "builder.tar", "stock_firmware/y203c/home_y203c.tgz",
                "stock_firmware/y203c/sys_y203c.tgz"}
    require(required <= seen, "Missing SDK/builder/source/stock image inputs")
    if source == BASE:
        inv = read_inventory()
        require({x["path"] for x in inv["files"]} <= seen, "Missing baseline archive")
        require(all(lock["submodules"].get(k) == v for k, v in inv["submodules"].items()),
                "Baseline Git dependency mismatch")
    return files


def stage_inputs(lock, source, inputs, stage):
    for entry in validate_lock(lock, source):
        rel = relative(entry["path"])
        original = inputs.joinpath(*rel.parts)
        require(original.resolve().is_relative_to(inputs.resolve()) and
                original.is_file() and not original.is_symlink(),
                "Missing or unsafe input: " + entry["path"])
        target = stage.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        require(digest(target) == entry["sha256"], "SHA-256 mismatch: " + entry["path"])


def command(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def docker_args(image, stage, work):
    return ["docker", "run", "--rm", "--pull=never", "--network=none",
            "--cap-drop=ALL", "--cap-add=CHOWN", "--cap-add=DAC_OVERRIDE",
            "--cap-add=FOWNER", "--security-opt=no-new-privileges",
            "--log-driver=none", "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev",
            "--mount", f"type=bind,src={stage},dst=/inputs,readonly",
            "--mount", f"type=bind,src={work},dst=/work",
            "--user", "0:0", "--env", f"FW008_OWNER_UID={os.getuid()}",
            "--env", f"FW008_OWNER_GID={os.getgid()}",
            "--entrypoint", "/bin/bash", image, "/inputs/build-offline.sh"]


def public_preflight(source, mode):
    require(source == BASE, "Hosted preflight accepts only the pinned baseline; use reviewed local lock for fork commits")
    print("Target: y203c; source: " + source)
    print("Public preflight: inventory present; private inputs NOT VERIFIED; full build NOT RUN.")
    require(mode != "full", "Hosted full build disabled: use trusted offline local build with approved inputs")


def local(args):
    require(sys.platform.startswith("linux"), "Use trusted Linux or WSL2")
    require(args.approved_lock_sha256 and DIGEST.fullmatch(args.approved_lock_sha256),
            "Supply independently reviewed lock SHA-256")
    require(args.lock and args.inputs, "Supply --lock and --inputs outside checkout")
    require(args.approved_entrypoint and SHA.fullmatch(args.approved_entrypoint),
            "Supply reviewed immutable --approved-entrypoint commit")
    actual = command(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip()
    require(actual == args.approved_entrypoint, "Unapproved entrypoint revision")
    status = command(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all",
                      "--ignored", "--", "ci/fw008"], capture_output=True, text=True).stdout
    require(not status, "Entrypoint directory must be pristine (including ignored files)")
    inputs = args.inputs.resolve()
    lock_path = args.lock.resolve()
    require(not inputs.is_relative_to(ROOT) and not lock_path.is_relative_to(ROOT),
            "Private inputs and lock must be outside repository")
    raw = lock_path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == args.approved_lock_sha256, "Lock digest mismatch")
    lock = json.loads(raw)
    validate_lock(lock, args.source)
    with tempfile.TemporaryDirectory(prefix="fw008-") as temp:
        stage = Path(temp) / "inputs"
        stage.mkdir()
        stage_inputs(lock, args.source, inputs, stage)
        print("Private input staging and SHA-256 checks passed; no firmware compiled yet.")
        if args.mode == "preflight":
            return
        require(args.output, "Full build requires a new private --output directory")
        output = args.output.resolve()
        require(not output.is_relative_to(ROOT) and not output.exists(), "Output must be new and outside checkout")
        require(shutil.which("docker"), "Docker CLI required")
        # Reject ambient remote daemon selection; use the reviewed local Unix socket.
        require(not os.environ.get("DOCKER_HOST") and not os.environ.get("DOCKER_CONTEXT"),
                "Unset Docker host/context overrides; use trusted local default context")
        endpoint = command(["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
                           capture_output=True, text=True).stdout.strip()
        require(endpoint == "unix:///var/run/docker.sock", "Trusted local Docker socket required")
        output.mkdir(mode=0o700)
        work = Path(temp) / "work"
        work.mkdir()
        (stage / "lock.json").write_text(json.dumps(lock))
        shutil.copyfile(ROOT / "ci/fw008/build-offline.sh", stage / "build-offline.sh")
        shutil.copyfile(ROOT / "ci/fw008/verify-source.py", stage / "verify-source.py")
        shutil.copyfile(ROOT / "ci/fw008/download-guard.sh", stage / "download-guard.sh")
        with (output / "private-build.log").open("wb") as log:
            command(["docker", "load", "--input", str(stage / "builder.tar")],
                    stdout=log, stderr=subprocess.STDOUT)
            info = json.loads(command(["docker", "image", "inspect", lock["image_id"]],
                                      capture_output=True, text=True).stdout)[0]
            require(info["Id"] == lock["image_id"] and info["Architecture"] == "amd64" and
                    not info["Config"].get("Volumes") and info["Os"] == "linux",
                    "Unexpected builder identity/platform/volumes")
            command(docker_args(lock["image_id"], stage, work), stdout=log, stderr=subprocess.STDOUT)
        result = work / "source/out/y203c"
        expected = [result / "home_y203c", result / "sys_y203c"]
        archives = list(result.glob("y203c_*.tgz"))
        require(len(archives) == 1, "Expected exactly one update archive")
        expected += archives
        require(all(p.is_file() and not p.is_symlink() and p.stat().st_size > 0 for p in expected),
                "Missing/empty firmware outputs")
        checksums = {}
        for p in expected:
            dest = output / p.name
            shutil.copyfile(p, dest)
            checksums[p.name] = digest(dest)
        entrypoint = actual
        (output / "metadata.json").write_text(json.dumps({
            "target": "y203c", "source_sha": args.source, "entrypoint_sha": entrypoint,
            "workflow_sha": None, "lock_sha256": args.approved_lock_sha256,
            "submodules": lock["submodules"], "builder_image": lock["image_id"],
            "output_sha256": checksums, "release_approved": False
        }, indent=2) + "\n")
        print("Full local build produced private outputs; NOT release-approved.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "full"], default="preflight")
    parser.add_argument("--source", default=BASE)
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--approved-lock-sha256")
    parser.add_argument("--approved-entrypoint")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.public:
            public_preflight(args.source, args.mode)
        else:
            local(args)
    except (Blocked, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as e:
        # Do not print arbitrary command output or private paths.
        print("BLOCKED: " + (str(e) if isinstance(e, Blocked) else
                            type(e).__name__ + "; inspect private inputs/log locally"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
