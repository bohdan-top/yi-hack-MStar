#!/bin/bash
set -euo pipefail
umask 077
# Return ownership of disposable bind-mount contents even on build failure.
trap 'chown -hR "$FW008_OWNER_UID:$FW008_OWNER_GID" /work; find /work -type d -exec chmod u+rwx {} +' EXIT
export HOME=/tmp
# Host configure tests require executable temporary files; /tmp stays noexec.
mkdir -p /work/tmp
export TMPDIR=/work/tmp
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
# FW-001: cap upstream nproc and explicit make -j options without editing
# tracked firmware files. Recursive make retains its inherited jobserver
# when no explicit parallelism override is supplied.
if [[ -n "${FW008_JOBS:-}" ]]; then
    [[ "$FW008_JOBS" =~ ^[1-9][0-9]*$ ]]
    command -v /usr/bin/make >/dev/null
    cat > /work/guards/nproc <<'GUARD'
#!/bin/bash
printf '%s\n' "$FW008_JOBS"
GUARD
    cat > /work/guards/make <<'GUARD'
#!/bin/bash
set -euo pipefail
args=()
while (($#)); do
    case "$1" in
        -j|--jobs)
            args+=("-j$FW008_JOBS")
            shift
            if (($#)) && [[ "$1" =~ ^[0-9]+$ ]]; then shift; fi
            ;;
        -j[0-9]*|--jobs=*)
            args+=("-j$FW008_JOBS")
            shift
            ;;
        *)
            args+=("$1")
            shift
            ;;
    esac
done
exec /usr/bin/make "${args[@]}"
GUARD
    chmod 755 /work/guards/{nproc,make}
    # Verify the intended cross-compiler and ELF ABI before compiling firmware.
    [[ "$(arm-linux-gnueabihf-gcc -dumpversion)" == "4.8.3" ]]
    printf 'int main(void) { return 0; }\n' > /work/arm-smoke.c
    arm-linux-gnueabihf-gcc /work/arm-smoke.c -o /work/arm-smoke
    arm-linux-gnueabihf-readelf -h /work/arm-smoke > /work/arm-smoke.elf
    grep -Eq 'Machine:[[:space:]]+ARM' /work/arm-smoke.elf
    grep -q 'hard-float ABI' /work/arm-smoke.elf
    echo "ARM ELF smoke test passed (device runtime compatibility not established)."
fi
tar -xf /inputs/source.tar -C /work/source
python3 /inputs/verify-source.py
cd /work/source
# Stage only verified files; reject collisions and symlink destinations.
PYTHONPATH=/inputs python3 -B - <<'PY'
import json
from pathlib import Path
import shutil
from baseline_aliases import apply_baseline_aliases
root = Path.cwd()
lock = json.loads(Path("/inputs/lock.json").read_text())
for entry in lock["files"]:
    rel = entry["path"]
    if rel in ("source.tar", "builder.tar"):
        continue
    dest = root / rel
    if dest.exists() or dest.is_symlink() or not dest.parent.resolve().is_relative_to(root):
        raise RuntimeError("Unexpected archive destination")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path("/inputs") / rel, dest)
apply_baseline_aliases(root, lock)
PY
# No mtd devices, mounts, sudo, camera or network are available. Stock tgz only.
bash -e scripts/init_sysroot.sh y203c
check_download /work/unexpected-download
bash -e scripts/compile.sh
check_download /work/unexpected-download
bash -e scripts/pack_fw.sh y203c
check_download /work/unexpected-download
