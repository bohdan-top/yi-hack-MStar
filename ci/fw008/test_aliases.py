import hashlib
from pathlib import Path
import tempfile
import sys
import unittest
import zipfile
from baseline_aliases import apply_baseline_aliases, BASE


class AliasTests(unittest.TestCase):
    def fixture(self, root):
        mbed = root / "src/onvif_simple_server/mbedtls-3.6.5.tar.bz2"
        mbed.parent.mkdir(parents=True)
        mbed.write_bytes(b"verified synthetic archive")
        mdnsd = root / "src/mdnsd/mdnsd-master.zip"
        mdnsd.parent.mkdir(parents=True)
        commit = "a" * 40
        with zipfile.ZipFile(mdnsd, "w") as z:
            z.writestr("mdnsd-" + commit + "/autogen.sh", "fixture")
        lock = {"source_sha": BASE, "files": [
            {"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
             "version": commit} for p in (mbed, mdnsd)]}
        return mbed, mdnsd, lock

    @unittest.skipIf(sys.platform == "win32", "Linux symlink fixture; run in WSL2")
    def test_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            mbed, mdnsd, lock = self.fixture(root)
            apply_baseline_aliases(root, lock)
            self.assertEqual(mbed.with_name("3.6.5.tar.gz").read_bytes(), mbed.read_bytes())
            with zipfile.ZipFile(mdnsd) as z:
                z.extractall(mdnsd.parent)
            self.assertEqual((mdnsd.with_name("mdnsd-master") / "autogen.sh").read_text(), "fixture")

    def test_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            mbed, _, lock = self.fixture(root)
            mbed.write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
                apply_baseline_aliases(root, lock)

    def test_collision(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            mbed, _, lock = self.fixture(root)
            mbed.with_name("3.6.5.tar.gz").write_bytes(b"unreviewed")
            with self.assertRaisesRegex(RuntimeError, "Unsafe"):
                apply_baseline_aliases(root, lock)
