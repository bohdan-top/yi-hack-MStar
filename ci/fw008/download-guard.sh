#!/bin/bash
# Fail closed if an upstream downloader is invoked, even if its failure is ignored.
install_download_guard() {
    local dir=$1 marker=$2
    mkdir -p "$dir"
    cat >"$dir/wget" <<'GUARD'
#!/bin/sh
touch "$FW008_DOWNLOAD_MARKER"
echo "Unexpected download blocked" >&2
exit 97
GUARD
    chmod +x "$dir/wget"
    local tool
    for tool in curl fetch ftp; do ln -s wget "$dir/$tool"; done
    export FW008_DOWNLOAD_MARKER="$marker"
    export PATH="$dir:$PATH"
}
check_download() {
    if test -e "$1"; then
        echo "BLOCKED: upstream attempted an unexpected download" >&2
        return 1
    fi
}
