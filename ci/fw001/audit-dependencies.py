#!/usr/bin/env python3
"""Inventory pinned Git build instructions without executing firmware code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

BASE = 'c8582405b2c3c0e3b80219b0e71e21785a482867'
PATTERN = re.compile(r'https?://|\b(?:wget|curl|git clone|FetchContent|ExternalProject)\b|/opt/|libOMX|mi_sys|mi_venc|msc3|sigmastar', re.I)


def audit(root):
    def git(path, *args):
        return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
                                        '-C', str(path), *args])
    files, submodules = {}, {}

    def walk(path, commit, prefix=''):
        if git(path, 'rev-parse', 'HEAD').decode().strip() != commit:
            raise ValueError('Unexpected source/submodule HEAD')
        if git(path, 'status', '--porcelain', '--untracked-files=all', '--ignored', '--ignore-submodules=none'):
            raise ValueError('Source/submodule must be pristine')
        for row in git(path, 'ls-tree', '-r', '-z', commit).split(b'\0'):
            if not row:
                continue
            meta, rawname = row.split(b'\t', 1)
            mode, kind, sha = meta.decode().split()
            name = rawname.decode()
            rel = prefix + name
            if mode == '160000':
                submodules[rel] = sha
                walk(path / name, sha, rel + '/')
            elif kind == 'blob' and mode in ('100644', '100755'):
                files[rel] = git(path, 'cat-file', 'blob', sha)

    walk(root, BASE)
    buildfiles, references = [], []
    for name, data in sorted(files.items()):
        p = Path(name)
        is_build = (p.name.startswith(('init.', 'compile.', 'install.', 'config.', 'Makefile')) or
                    p.name in ('configure.ac', 'configure.in', 'CMakeLists.txt', '.gitmodules') or
                    p.suffix in ('.cmake', '.am', '.mk') or name.startswith('scripts/'))
        if is_build:
            buildfiles.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest()})
        if is_build or p.suffix in ('.c', '.h', '.cpp'):
            for line, text in enumerate(data.decode('utf8', errors='replace').splitlines(), 1):
                if PATTERN.search(text):
                    references.append({'path': name, 'line': line, 'text': text.strip()})
    modules = sorted({name.split('/')[1] for name in files if name.startswith('src/')})
    return {'schema': 1, 'source_sha': BASE, 'tracked_files_read': len(files),
            'recursive_submodules': submodules, 'modules': modules,
            'build_instruction_files': buildfiles, 'dependency_references': references,
            'scope': 'Static tracked Git source audit; generated build instructions and compilation remain separate checks'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source_dir)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Audited {len(result['modules'])} modules, {len(result['recursive_submodules'])} recursive gitlinks, "
          f"{len(result['build_instruction_files'])} build instruction files.")


if __name__ == '__main__':
    main()
