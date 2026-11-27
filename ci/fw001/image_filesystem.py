"""Read pristine JFFS2 userspace images without mounts, devices or extraction.

CRC/bounds validation is shared with image_structure. Unsupported compression,
node flags and filesystem types fail closed. This is not a kernel emulator.
"""
import stat
import struct
import zlib
import hashlib
import json
from pathlib import Path, PurePosixPath

from image_structure import ERASE_SIZE, INODE, DIRENT, InvalidImage, check, inspect_image


def read_tree(path, limit):
    structure = inspect_image(path, limit)
    data = Path(path).read_bytes()
    inodes, dirents = {}, {}
    for start in range(0, len(data), ERASE_SIZE):
        block = data[start:start + ERASE_SIZE]
        pos = 0
        while pos < len(block) and block[pos:pos + 4] != b'\xff' * 4:
            _, kind, length, _ = struct.unpack_from('<HHII', block, pos)
            node = block[pos:pos + length]
            if kind == INODE:
                ino, version, mode = struct.unpack_from('<III', node, 12)
                uid, gid = struct.unpack_from('<HH', node, 24)
                size, atime, mtime, ctime, offset, csize, dsize = struct.unpack_from('<IIIIIII', node, 28)
                check(0 < ino and size <= limit and dsize <= min(limit, 1024 * 1024), 'Invalid logical inode size')
                check(offset <= size and dsize <= size - offset, 'Inode fragment exceeds logical size')
                check(struct.unpack_from('<H', node, 58)[0] == 0, 'Unsupported inode flags')
                packed = node[68:]
                if node[56] in (0, 4):
                    content = packed
                elif node[56] == 1:
                    check(csize == 0, 'ZERO fragment contains data')
                    content = bytes(dsize)
                elif node[56] == 6:
                    decoder = zlib.decompressobj()
                    try:
                        content = decoder.decompress(packed, dsize + 1)
                    except zlib.error as error:
                        raise InvalidImage('Invalid zlib payload') from error
                    check(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                          'Invalid or oversized zlib payload')
                else:
                    check(False, 'Unsupported JFFS2 compression')
                check(len(content) == dsize, 'Decompressed size mismatch')
                fragments = inodes.setdefault(ino, {})
                check(version not in fragments, 'Duplicate inode version')
                fragments[version] = dict(mode=mode, uid=uid, gid=gid, size=size,
                                          mtime=mtime, offset=offset, data=content)
            elif kind == DIRENT:
                parent, version, ino = struct.unpack_from('<III', node, 12)
                name = node[40:].decode('utf8')
                check(name not in ('.', '..') and '\\' not in name, 'Unsafe filesystem name')
                key = parent, name
                check(key not in dirents or dirents[key][0] != version, 'Duplicate dirent version')
                if key not in dirents or dirents[key][0] < version:
                    dirents[key] = version, ino, node[29]
            pos += (length + 3) & ~3

    check(sum(versions[max(versions)]['size'] for versions in inodes.values()) <= limit * 32,
          'Filesystem logical allocation exceeds validation budget')
    resolved = {}
    for ino, versions in inodes.items():
        latest = versions[max(versions)]
        mode, size = latest['mode'], latest['size']
        check(stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode), 'Unsupported filesystem type')
        body = bytearray(size)
        for version, part in sorted(versions.items()):
            check(stat.S_IFMT(part['mode']) == stat.S_IFMT(mode), 'Inode type changed')
            begin = min(part['offset'], size)
            end = min(part['offset'] + len(part['data']), size)
            body[begin:end] = part['data'][:end - begin]
        if stat.S_ISLNK(mode):
            check(0 < len(body) <= 4095 and b'\x00' not in body, 'Invalid symlink contents')
        resolved[ino] = {**latest, 'data': bytes(body)}

    children = {}
    check(1 not in resolved or stat.S_ISDIR(resolved[1]['mode']), 'Root inode is not a directory')
    for (parent, name), (_, ino, dtype) in dirents.items():
        if ino:
            check(ino in resolved, 'Dangling directory entry')
            children.setdefault(parent, []).append((name, ino, dtype))
    tree = {}
    visited_dirs = set()

    def visit(ino, prefix, ancestors):
        check(ino not in ancestors and len(ancestors) < 100, 'Filesystem directory cycle/depth')
        check(ino not in visited_dirs, 'Directory is linked more than once')
        visited_dirs.add(ino)
        for name, child, dtype in sorted(children.get(ino, [])):
            entry = resolved[child]
            path = (PurePosixPath(prefix) / name).as_posix()
            check(path not in tree, 'Duplicate filesystem path')
            expected = 4 if stat.S_ISDIR(entry['mode']) else 10 if stat.S_ISLNK(entry['mode']) else 8
            check(dtype in (0, expected), 'Directory entry type mismatch')
            tree[path] = entry
            if stat.S_ISDIR(entry['mode']):
                visit(child, path, ancestors | {ino})
            else:
                check(child not in children, 'Non-directory has children')

    visit(1, '', set())
    check(all(parent in visited_dirs for parent in children), 'Unreachable filesystem directory')
    return tree, structure


def identities(tree):
    result = {}
    for name in ('homever', 'app/.appver', 'yi-hack/version', 'yi-hack/model_suffix'):
        if name in tree:
            entry = tree[name]
            check(stat.S_ISREG(entry['mode']) and len(entry['data']) <= 4096, 'Invalid identity file')
            result[name] = entry['data'].decode('utf8').strip('\x00\r\n ')
    return result


def inspect_firmware_pair(folder):
    from image_structure import CANDIDATE_LIMITS
    result = {}
    for name, limit in CANDIDATE_LIMITS.items():
        tree, structure = read_tree(Path(folder) / name, limit)
        identity = identities(tree)
        if name == 'home_y203c':
            check(identity.get('yi-hack/version') == '0.5.8', 'Wrong hack version')
            check(identity.get('yi-hack/model_suffix') == 'y203c', 'Wrong model suffix')
            check(identity.get('homever') == '4.5.0.0C_201910080934', 'Wrong base version')
            check(identity.get('app/.appver') == '4.5.0.0C_201910080934', 'Wrong app base version')
        rows = [dict(path=path, mode=entry['mode'], uid=entry['uid'], gid=entry['gid'],
                     sha256=hashlib.sha256(entry['data']).hexdigest()) for path, entry in sorted(tree.items())]
        content = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        for row in rows:
            row['mtime'] = tree[row['path']]['mtime']
        result[name] = dict(structure=structure, identities=identity, filesystem_entries=len(tree),
            content_manifest_sha256=content,
            timestamped_manifest_sha256=hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest())
    return result
