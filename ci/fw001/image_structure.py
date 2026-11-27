"""Strict structural checks for fresh, little-endian upstream mkfs.jffs2 images.

Not a filesystem mount, decompression check, device compatibility test or release
approval. Reject unknown node types rather than silently accepting them.
Layout: Linux include/uapi/linux/jffs2.h; erase size: pinned scripts/pack_fw.sh.
Candidate size ceilings: upstream wiki Dump-your-backup-firmware example;
actual 6FUS hardware geometry must still be independently confirmed.
"""
import struct
import zlib
from pathlib import Path

ERASE_SIZE = 0x10000
CANDIDATE_LIMITS = {"home_y203c": 0xC30000, "sys_y203c": 0x1E0000}
DIRENT, INODE, CLEANMARKER, PADDING = 0xE001, 0xE002, 0x2003, 0x2004


class InvalidImage(ValueError):
    pass


def check(condition, message):
    if not condition:
        raise InvalidImage(message)


def crc(data):
    # Linux crc32(0, data, len): no initial/final complement.
    return zlib.crc32(data, 0xFFFFFFFF) ^ 0xFFFFFFFF


def u32(data, pos):
    return struct.unpack_from("<I", data, pos)[0]


def inspect_image(path, limit):
    """Scan every node and verify stored header, inode/data and dirent/name CRCs."""
    path = Path(path)
    check(path.is_file() and not path.is_symlink(), "Missing or unsafe image")
    size = path.stat().st_size
    check(0 < size <= limit, "Image exceeds candidate partition limit or is empty")
    check(size % 4 == 0, "Image size is not word aligned")
    counts = {"inodes": 0, "dirents": 0, "cleanmarkers": 0, "padding": 0}
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    check(len(data) == size, "Image changed during read")
    for start in range(0, size, ERASE_SIZE):
        block = data[start:start + ERASE_SIZE]
        pos = 0
        while pos < len(block):
            # mkfs.jffs2 may leave erased space at the end of an eraseblock.
            if block[pos:pos + 4] == b"\xff" * 4:
                check(all(b == 0xFF for b in block[pos:]), "Non-erased data after erased gap")
                break
            check(len(block) - pos >= 12, "Truncated node header")
            magic, kind, length, header_crc = struct.unpack_from("<HHII", block, pos)
            check(magic == 0x1985, "Invalid little-endian JFFS2 magic")
            check(length >= 12 and length <= len(block) - pos, "Node crosses eraseblock or image boundary")
            check(crc(block[pos:pos + 8]) == header_crc, "Header CRC mismatch")
            node = block[pos:pos + length]
            if kind == INODE:
                check(length >= 68 and length == 68 + u32(node, 48), "Invalid inode data length")
                check(crc(node[:60]) == u32(node, 64), "Inode CRC mismatch")
                check(crc(node[68:]) == u32(node, 60), "Inode data CRC mismatch")
                counts["inodes"] += 1
            elif kind == DIRENT:
                check(length >= 40 and node[28] > 0 and length == 40 + node[28],
                      "Invalid dirent name length")
                check(crc(node[:32]) == u32(node, 32), "Dirent CRC mismatch")
                check(crc(node[40:]) == u32(node, 36), "Dirent name CRC mismatch")
                check(b"\x00" not in node[40:] and b"/" not in node[40:], "Invalid dirent name")
                counts["dirents"] += 1
            elif kind == CLEANMARKER:
                check(length == 12 and pos == 0, "Invalid cleanmarker")
                counts["cleanmarkers"] += 1
            elif kind == PADDING:
                counts["padding"] += 1
            else:
                raise InvalidImage("Unsupported node type in pristine image")
            aligned = (length + 3) & ~3
            check(pos + aligned <= len(block), "Truncated alignment padding")
            check(all(b == 0xFF for b in block[pos + length:pos + aligned]),
                  "Non-erased alignment padding")
            pos += aligned
    check(counts["inodes"] > 0 and counts["dirents"] > 0, "No filesystem inode/dirent nodes")
    return {"bytes": size, "candidate_limit_bytes": limit, **counts}


def inspect_pair(folder):
    return {name: inspect_image(Path(folder) / name, limit)
            for name, limit in CANDIDATE_LIMITS.items()}
