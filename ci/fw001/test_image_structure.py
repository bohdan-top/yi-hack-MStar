import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("image_structure", Path(__file__).with_name("image_structure.py"))
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


def header(kind, length):
    prefix = struct.pack("<HHI", 0x1985, kind, length)
    return prefix + struct.pack("<I", image.crc(prefix))


def align(node):
    return node + b"\xff" * (-len(node) % 4)


def inode(payload=b"abc"):
    raw = bytearray(header(image.INODE, 68 + len(payload)) + bytes(56))
    struct.pack_into("<I", raw, 12, 2)
    struct.pack_into("<I", raw, 48, len(payload))
    struct.pack_into("<I", raw, 52, len(payload))
    struct.pack_into("<I", raw, 60, image.crc(payload))
    struct.pack_into("<I", raw, 64, image.crc(raw[:60]))
    return align(raw + payload)


def dirent(name=b"test"):
    raw = bytearray(header(image.DIRENT, 40 + len(name)) + bytes(28))
    struct.pack_into("<I", raw, 12, 1)
    struct.pack_into("<I", raw, 20, 2)
    raw[28] = len(name)
    struct.pack_into("<I", raw, 32, image.crc(raw[:32]))
    struct.pack_into("<I", raw, 36, image.crc(name))
    return align(raw + name)


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "image"
        self.valid = header(image.CLEANMARKER, 12) + dirent() + inode()

    def inspect(self, data, limit=0x20000):
        self.path.write_bytes(data)
        return image.inspect_image(self.path, limit)

    def test_kernel_crc_vector(self):
        self.assertEqual(image.crc(b"123456789"), 0x2DFD2D88)

    def test_valid_and_erased_block(self):
        padded = self.valid + b"\xff" * (image.ERASE_SIZE - len(self.valid))
        result = self.inspect(padded + self.valid)
        self.assertEqual(result["inodes"], 2)
        self.assertEqual(result["dirents"], 2)

    def test_corruption(self):
        for offset in (0, 8, 12 + 32, 12 + 40, 12 + len(dirent()) + 64,
                       12 + len(dirent()) + 68, len(self.valid) - 1):
            with self.subTest(offset=offset):
                data = bytearray(self.valid)
                data[offset] ^= 1
                with self.assertRaises(image.InvalidImage):
                    self.inspect(data)

    def test_bad_size_and_truncation(self):
        for data, limit in ((b"", 100), (self.valid, 10),
                            (self.valid[:-1], 1000), (self.valid[:-4], 1000)):
            with self.subTest(length=len(data), limit=limit):
                with self.assertRaises(image.InvalidImage):
                    self.inspect(data, limit)

    def test_erased_gap_unknown_and_missing_nodes(self):
        for data in (self.valid + b"\xff" * 4 + b"oops",
                     self.valid + header(0x2006, 12),
                     header(image.CLEANMARKER, 12), b"\xff" * 64):
            with self.subTest(length=len(data)):
                with self.assertRaises(image.InvalidImage):
                    self.inspect(data)

    def test_oversized_node_cannot_cross_eraseblock(self):
        with self.assertRaises(image.InvalidImage):
            self.inspect(header(image.PADDING, image.ERASE_SIZE + 4) +
                         b"\xff" * (image.ERASE_SIZE - 8))


if __name__ == "__main__":
    unittest.main()
