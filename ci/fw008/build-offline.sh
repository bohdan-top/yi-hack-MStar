#!/bin/bash
set -euo pipefail
umask 077
# Return ownership of disposable bind-mount contents even on build failure.
trap 'chown -hR "$FW008_OWNER_UID:$FW008_OWNER_GID" /work; find /work -type d -exec chmod u+rwx {} +' EXIT
export HOME=/tmp
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null
export GIT_CONFIG_KEY_1=core.fsmonitor GIT_CONFIG_VALUE_1=false
export PATH=/work/guards:/opt/yi/arm-linux-gnueabihf-4.8.3-201404/bin:/usr/local/bin:/usr/bin:/bin
for tool in git python3 tar unzip rsync mkfs.jffs2 7za make patch autoconf automake libtoolize \
    arm-linux-gnueabihf-gcc arm-linux-gnueabihf-g++ arm-linux-gnueabihf-strip; do
    command -v "$tool" >/dev/null || { echo "Missing builder tool: $tool"; exit 1; }
done
mkdir /work/source /work/guards
source /inputs/download-guard.sh
install_download_guard /work/guards /work/unexpected-download
tar -xf /inputs/source.tar -C /work/source
python3 /inputs/verify-source.py
cd /work/source
# Stage only verified files; reject collisions and symlink destinations.
python3 - <<'PY'
import json
from pathlib import Path
import shutil
root = Path.cwd()
for entry in json.loads(Path("/inputs/lock.json").read_text())["files"]:
    rel = entry["path"]
    if rel in ("source.tar", "builder.tar"):
        continue
    dest = root / rel
    if dest.exists() or dest.is_symlink() or not dest.parent.resolve().is_relative_to(root):
        raise RuntimeError("Unexpected archive destination")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path("/inputs") / rel, dest)
PY
# No mtd devices, mounts, sudo, camera or network are available. Stock tgz only.
bash scripts/init_sysroot.sh y203c
check_download /work/unexpected-download
bash scripts/compile.sh
check_download /work/unexpected-download
bash scripts/pack_fw.sh y203c
check_download /work/unexpected-download
