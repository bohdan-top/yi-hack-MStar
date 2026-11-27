import copy
import hashlib
import io
import tarfile
import importlib.util
import pathlib
import tempfile
import subprocess
import os
import sys
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location("build", pathlib.Path(__file__).with_name("manual-build.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class Bootstrap(unittest.TestCase):
    def fixture(self, inputs):
        lock = copy.deepcopy(build.read_inventory())
        lock["review_status"] = "approved"
        lock["image_id"] = "sha256:" + "a" * 64
        lock["additional_inputs"] = [{"source": "synthetic", "version": "fixture", "sha256": "b" * 64}]
        for item in lock["files"]:
            p = inputs / item["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(item["path"].encode())
            item["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            if item["path"] != "src/mdnsd/mdnsd-master.zip":
                item["version"] = "synthetic-fixture"
        # Synthetic archive digests have a separate synthetic trust inventory.
        inventory_patch = patch.object(build, "read_inventory", return_value=copy.deepcopy(lock))
        inventory_patch.start()
        self.addCleanup(inventory_patch.stop)
        return lock

    def test_public_and_unapproved_ref(self):
        build.public_preflight(build.BASE, "preflight")
        with self.assertRaises(build.Blocked):
            build.public_preflight("a" * 40, "preflight")
        with self.assertRaises(build.Blocked):
            build.public_preflight(build.BASE, "full")

    def test_verified_clean_stage_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            inputs = pathlib.Path(d) / "inputs"
            inputs.mkdir()
            lock = self.fixture(inputs)
            stage = pathlib.Path(d) / "stage"
            build.stage_inputs(lock, build.BASE, inputs, stage)
            self.assertEqual(len(list(p for p in stage.rglob("*") if p.is_file())), len(lock["files"]))
            (inputs / "source.tar").write_bytes(b"tampered")
            with self.assertRaisesRegex(build.Blocked, "SHA-256 mismatch"):
                build.stage_inputs(lock, build.BASE, inputs, pathlib.Path(d) / "new")

    def test_lock_cannot_override_independently_pinned_public_digest(self):
        with tempfile.TemporaryDirectory() as d:
            lock = self.fixture(pathlib.Path(d))
            public = next(x for x in lock["files"] if x["path"].startswith("src/"))
            public["sha256"] = "0" * 64
            with self.assertRaisesRegex(build.Blocked, "independent public provenance"):
                build.validate_lock(lock, build.BASE)

    def test_missing_input_and_unapproved_lock(self):
        with tempfile.TemporaryDirectory() as d:
            inputs = pathlib.Path(d)
            lock = self.fixture(inputs)
            (inputs / "builder.tar").unlink()
            with self.assertRaisesRegex(build.Blocked, "Missing or unsafe"):
                build.stage_inputs(lock, build.BASE, inputs, inputs / "new")
            lock["review_status"] = "unreviewed"
            with self.assertRaisesRegex(build.Blocked, "not approved"):
                build.validate_lock(lock, build.BASE)

    def test_reject_unpinned_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            lock = self.fixture(pathlib.Path(d))
            lock["submodules"]["nested"] = "master"
            with self.assertRaises(build.Blocked):
                build.validate_lock(lock, build.BASE)
            with self.assertRaises(build.Blocked):
                build.relative("../outside")

    def test_unexpected_download_even_if_upstream_ignores_failure(self):
        with tempfile.TemporaryDirectory() as d:
            script = pathlib.Path(__file__).with_name("download-guard.sh")
            result = subprocess.run([os.environ.get("FW008_TEST_BASH", "bash"), "-c", 'set -e; script=$1; base=$2; if command -v cygpath >/dev/null; then script=$(cygpath -u "$script"); base=$(cygpath -u "$base"); fi; source "$script"; install_download_guard "$base/guards" "$base/marker"; check_download "$base/marker"; wget https://example.invalid || true; check_download "$base/marker"', "bash", script.as_posix(), pathlib.Path(d).as_posix()], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((pathlib.Path(d) / "marker").exists())
            self.assertIn("unexpected download", result.stderr)

    def test_verified_output_archive(self):
        with tempfile.TemporaryDirectory() as d:
            work = pathlib.Path(d)
            result = work / "source/out/y203c"
            result.mkdir(parents=True)
            images = {"home_y203c": b"home image", "sys_y203c": b"system image"}
            for name, data in images.items():
                (result / name).write_bytes(data)
            bundle = result / "y203c_test.tgz"

            def write_archive(entries):
                with tarfile.open(bundle, "w:gz") as archive:
                    for name, data in entries.items():
                        info = tarfile.TarInfo(name)
                        info.size = len(data)
                        archive.addfile(info, io.BytesIO(data))

            write_archive(images)
            self.assertEqual(len(build.verified_outputs(work)), 3)
            write_archive({**images, "home_y203c": b"HOME IMAGE"})
            with self.assertRaisesRegex(build.Blocked, "image mismatch"):
                build.verified_outputs(work)
            write_archive({**images, "extra": b"extra"})
            with self.assertRaisesRegex(build.Blocked, "archive members"):
                build.verified_outputs(work)
            write_archive(images)
            if sys.platform == "win32":
                return  # The separate Linux directory-symlink test covers ancestry.
            (result / "home_y203c").unlink()
            (result / "home_y203c").symlink_to("sys_y203c")
            with self.assertRaisesRegex(build.Blocked, "Missing/empty"):
                build.verified_outputs(work)

    @unittest.skipIf(sys.platform == "win32", "Linux symlink fixture; run in WSL2")
    def test_output_directory_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            work = pathlib.Path(d) / "work"
            work.mkdir()
            other = pathlib.Path(d) / "other"
            (other / "out/y203c").mkdir(parents=True)
            (work / "source").symlink_to(other, target_is_directory=True)
            with self.assertRaisesRegex(build.Blocked, "Unsafe firmware output directory"):
                build.verified_outputs(work)

    def test_isolation_command(self):
        with patch.object(build.os, "getuid", return_value=1000, create=True), \
                patch.object(build.os, "getgid", return_value=1000, create=True):
            args = build.docker_args("sha256:" + "a" * 64, "/private/inputs", "/private/work")
        for token in ("--network=none", "--pull=never", "--read-only", "--cap-drop=ALL",
                      "--security-opt=no-new-privileges", "--log-driver=none"):
            self.assertIn(token, args)
        self.assertNotIn("--privileged", args)


if __name__ == "__main__":
    unittest.main()
