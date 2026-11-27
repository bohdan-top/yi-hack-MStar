from pathlib import Path
import stat
import struct
import tempfile
import unittest
import zlib

from image_structure import crc, InvalidImage, INODE, DIRENT
from image_filesystem import read_tree, identities, inspect_firmware_pair


def node(kind, body):
    header = struct.pack('<HHI', 0x1985, kind, 12 + len(body))
    data = header + struct.pack('<I', crc(header)) + body
    return data + b'\xff' * (-len(data) % 4)


def inode(ino=2, body=b'0.5.8\n', compression=6, version=1, offset=0, size=None,
          mode=stat.S_IFREG | 0o644, packed=None):
    if packed is None:
        packed = zlib.compress(body) if compression == 6 else body
    raw = bytearray(56)
    struct.pack_into('<IIIHHIIIIIII', raw, 0, ino, version, mode, 0, 0,
                     len(body) if size is None else size, 0, 0, 0, offset, len(packed), len(body))
    raw[44] = compression
    struct.pack_into('<I', raw, 48, crc(packed))
    # Inode CRC includes the complete common header.
    prefix = struct.pack('<HHI', 0x1985, INODE, 68 + len(packed))
    header = prefix + struct.pack('<I', crc(prefix))
    struct.pack_into('<I', raw, 52, crc(header + raw[:48]))
    return node(INODE, raw + packed)


def dirent(parent=1, ino=2, name=b'version', dtype=8):
    raw = bytearray(28)
    struct.pack_into('<III', raw, 0, parent, 1, ino)
    raw[16], raw[17] = len(name), dtype
    prefix = struct.pack('<HHI', 0x1985, DIRENT, 40 + len(name))
    header = prefix + struct.pack('<I', crc(prefix))
    struct.pack_into('<II', raw, 20, crc(header + raw[:20]), crc(name))
    return node(DIRENT, raw + name)


class FilesystemTests(unittest.TestCase):
    def read(self, data):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'image'
            path.write_bytes(data)
            return read_tree(path, 0x20000)[0]

    def test_zlib_file_and_identity(self):
        tree = self.read(dirent(name=b'homever') + inode())
        self.assertEqual(identities(tree), {'homever': '0.5.8'})

    def test_bad_zlib_with_valid_node_crcs(self):
        for packed in (b'invalid', zlib.compress(b'0.5.8\n') + b'trailing', zlib.compress(b'too much data')):
            with self.subTest(packed=packed), self.assertRaises((InvalidImage, zlib.error)):
                self.read(dirent() + inode(packed=packed))

    def test_semantic_rejections(self):
        for data in (dirent(ino=3) + inode(), dirent(name=b'..') + inode(),
                     dirent(dtype=4) + inode(), dirent() + inode(compression=7),
                     dirent(parent=3) + inode(), dirent() + inode(offset=9),
                     dirent(dtype=10) + inode(body=b'a\x00b', compression=0, mode=stat.S_IFLNK | 0o777)):
            with self.subTest(data=data), self.assertRaises(InvalidImage):
                self.read(data)

    def test_versions_and_symlink(self):
        tree = self.read(dirent() + inode(body=b'old', compression=0, size=3) +
                         inode(body=b'new', compression=0, version=2, size=3))
        self.assertEqual(tree['version']['data'], b'new')
        tree = self.read(dirent(dtype=10) + inode(body=b'/tmp', compression=0, mode=stat.S_IFLNK | 0o777))
        self.assertEqual(tree['version']['data'], b'/tmp')

    def test_directory_cycle(self):
        data = dirent(ino=2, name=b'a', dtype=4) + dirent(parent=2, ino=2, name=b'again', dtype=4)
        with self.assertRaises(InvalidImage):
            self.read(data + inode(mode=stat.S_IFDIR | 0o755, body=b'', compression=0))

    def test_duplicate_inode_version(self):
        with self.assertRaises(InvalidImage):
            self.read(dirent() + inode() + inode())

    def test_firmware_identity_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prefix = (dirent(name=b'homever', ino=2) + inode(ino=2, body=b'4.5.0.0C_201910080934\n') +
                dirent(name=b'yi-hack', ino=3, dtype=4) +
                inode(ino=3, mode=stat.S_IFDIR | 0o755, body=b'', compression=0) +
                dirent(parent=3, name=b'version', ino=4) + inode(ino=4) +
                dirent(parent=3, name=b'model_suffix', ino=5) +
                dirent(name=b'app', ino=6, dtype=4) +
                inode(ino=6, mode=stat.S_IFDIR | 0o755, body=b'', compression=0) +
                dirent(parent=6, name=b'.appver', ino=7) + inode(ino=7, body=b'4.5.0.0C_201910080934\n'))
            (root / 'sys_y203c').write_bytes(dirent() + inode())
            (root / 'home_y203c').write_bytes(prefix + inode(ino=5, body=b'y203c\n'))
            self.assertEqual(inspect_firmware_pair(root)['home_y203c']['identities']['yi-hack/version'], '0.5.8')
            (root / 'home_y203c').write_bytes(prefix + inode(ino=5, body=b'y25\n'))
            with self.assertRaisesRegex(InvalidImage, 'model suffix'):
                inspect_firmware_pair(root)
