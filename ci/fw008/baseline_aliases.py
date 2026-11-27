"""Compatibility staging for the pinned baseline, without editing tracked firmware."""
import hashlib
import re
from pathlib import Path
import zipfile

BASE = "c8582405b2c3c0e3b80219b0e71e21785a482867"


def apply_baseline_aliases(root, lock):
    if lock["source_sha"] != BASE:
        return
    entries = {entry["path"]: entry for entry in lock["files"]}
    mbed = root / "src/onvif_simple_server/mbedtls-3.6.5.tar.bz2"
    alias = mbed.with_name("3.6.5.tar.gz")
    # The upstream existence check uses the wrong name, but extraction uses
    # the correct file. Alias the real verified archive, never an empty sentinel.
    if alias.exists() or alias.is_symlink() or not mbed.is_file() or mbed.is_symlink():
        raise RuntimeError("Unsafe mbedTLS alias destination/input")
    with mbed.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != entries[
                "src/onvif_simple_server/mbedtls-3.6.5.tar.bz2"]["sha256"]:
            raise RuntimeError("mbedTLS staging digest mismatch")
    alias.symlink_to(mbed.name)
    # GitHub's immutable commit ZIP has a commit-suffixed root. Upstream
    # expects mdnsd-master. Keep the verified bytes and alias only the root.
    key = "src/mdnsd/mdnsd-master.zip"
    mdnsd = root / key
    entry = entries[key]
    commit = entry["version"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("mdnsd must be pinned to an immutable commit")
    expected_root = "mdnsd-" + commit
    with mdnsd.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != entry["sha256"]:
            raise RuntimeError("mdnsd staging digest mismatch")
    with zipfile.ZipFile(mdnsd) as archive:
        names = archive.namelist()
        if not names or any(name.split("/")[0] != expected_root or
                            ".." in Path(name).parts or "\\" in name
                            for name in names):
            raise RuntimeError("Unexpected mdnsd ZIP root")
    dest = mdnsd.with_name("mdnsd-master")
    extracted = mdnsd.with_name(expected_root)
    if any(p.exists() or p.is_symlink() for p in (dest, extracted)):
        raise RuntimeError("Unsafe mdnsd alias destination")
    dest.symlink_to(expected_root, target_is_directory=True)
