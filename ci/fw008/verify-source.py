#!/usr/bin/env python3
"""Verify source and recursive submodules before running upstream code."""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path("/work/source")
lock = json.loads(Path("/inputs/lock.json").read_text())
os.environ.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
                   "GIT_TERMINAL_PROMPT": "0"})


def git(path, *args):
    return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null",
                                    "-c", "core.fsmonitor=false", "-c", "safe.directory=*",
                                    "-C", str(path), *args])


seen = {}


def verify(path, expected):
    if git(path, "rev-parse", "HEAD").decode().strip() != expected:
        raise RuntimeError("Source commit mismatch")
    if git(path, "status", "--porcelain", "--untracked-files=all", "--ignored", "--ignore-submodules=none"):
        raise RuntimeError("Source bundle must be pristine, including ignored files")
    for row in git(path, "ls-tree", "-r", "-z", "HEAD").split(b"\0"):
        if not row:
            continue
        meta, name = row.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        if mode == "160000":
            child = path / os.fsdecode(name)
            rel = child.relative_to(root).as_posix()
            if child.is_symlink() or not child.is_dir() or not (child / ".git").exists():
                raise RuntimeError("Missing submodule checkout")
            seen[rel] = sha
            verify(child, sha)


verify(root, lock["source_sha"])
if seen != lock["submodules"]:
    raise RuntimeError("Recursive submodule lock mismatch")
print("Source and recursive gitlinks verified.")
