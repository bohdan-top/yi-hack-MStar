import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("runner", Path(__file__).with_name("run.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def test_container_limits_and_existing_isolation(self):
        with patch.object(runner.os, "sched_getaffinity", return_value=set(range(8)), create=True), \
                patch.object(runner.os, "getuid", return_value=1000, create=True), \
                patch.object(runner.os, "getgid", return_value=1000, create=True):
            args = runner.fw.docker_args("sha256:" + "a" * 64, "/stage", "/work", 6, 8)
            for flag, value in (("--cpus", "6"), ("--cpuset-cpus", "0,1,2,3,4,5"),
                                ("--memory", "8g"), ("--memory-swap", "8g")):
                self.assertEqual(args[args.index(flag) + 1], value)
            self.assertIn("--network=none", args)
            self.assertIn("--pull=never", args)
            with self.assertRaises(runner.fw.Blocked):
                runner.fw.docker_args("image", "/stage", "/work", 9, 8)

    def test_resume_rejects_tampered_output_and_changed_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = {"entrypoint": "a" * 40, "lock": "b" * 64, "image": "sha256:" + "c" * 64,
                   "cpus": 6, "memory_gib": 8}
            for name in runner.NAMES[:2]:
                (root / name).write_bytes(name.encode())
            with tarfile.open(root / runner.NAMES[2], "w:gz") as archive:
                for name in runner.NAMES[:2]:
                    data = (root / name).read_bytes()
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            hashes = {name: runner.fw.digest(root / name) for name in runner.NAMES}
            runner.atomic_json(root / "metadata.json", {
                "target": "y203c", "source_sha": runner.fw.BASE,
                "entrypoint_sha": key["entrypoint"], "lock_sha256": key["lock"],
                "builder_image": key["image"], "requested_cpus": 6,
                "requested_memory_gib": 8, "output_sha256": hashes,
                "release_approved": False})
            self.assertEqual(runner.verify_outputs(root, key), hashes)
            with self.assertRaises(runner.fw.Blocked):
                runner.verify_outputs(root, {**key, "cpus": 4})
            checkpoint = root / "checkpoint.json"
            # The fixture directory is selected through a task-owned primary name.
            with patch.object(runner, "verify_outputs", wraps=runner.verify_outputs):
                # A normal output name is required; use a real primary child.
                primary = root / ("primary-" + "d" * 32)
                primary.mkdir()
                for name in (*runner.NAMES, "metadata.json"):
                    (primary / name).write_bytes((root / name).read_bytes())
                runner.atomic_json(checkpoint, {"key": key, "directory": primary.name, "hashes": hashes})
                report = {}
                self.assertEqual(runner.resume_primary(checkpoint, root, key, report), (primary, hashes))
                self.assertTrue(report["primary_resumed"])
                report = {}
                self.assertIsNone(runner.resume_primary(checkpoint, root, {**key, "cpus": 4}, report))
                self.assertTrue(report["checkpoint_invalidated"])
                (primary / runner.NAMES[0]).write_bytes(b"tampered")
                report = {}
                self.assertIsNone(runner.resume_primary(checkpoint, root, key, report))
                self.assertTrue(report["checkpoint_invalidated"])
            (root / runner.NAMES[0]).write_bytes(b"tampered")
            with self.assertRaises(runner.fw.Blocked):
                runner.verify_outputs(root, key)

    def test_non_inventory_download_rejected_before_network(self):
        entry = {"path": "src/fake/x.tar.gz", "source": "https://example.invalid/x.tar.gz",
                 "version": "1", "sha256": hashlib.sha256(b"x").hexdigest()}
        with patch.object(runner.urllib.request, "urlopen") as network:
            with self.assertRaises(runner.fw.Blocked):
                runner.approved_download(entry, Path("/tmp/not-created"), 1, (), {})
            network.assert_not_called()


    def test_cache_hit_and_corrupted_cache_recovery(self):
        payload = b"synthetic dependency"
        entry = {"path": "src/example/archive.tar.gz", "source": "https://example.invalid/archive.tar.gz",
                 "version": "fixture", "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs, cache = root / "inputs", root / "cache"
            inputs.mkdir()
            cache.mkdir()
            cached = cache / entry["sha256"]
            cached.write_bytes(payload)
            stats = {"verified_cache_hits": 0, "verified_local_inputs": 0, "downloaded_bytes": 0}
            with patch.object(runner.fw, "validate_lock", return_value=[entry]), \
                    patch.object(runner, "approved_download") as download:
                runner.prepare_inputs({}, runner.fw.BASE, inputs, cache, root / "snapshot", 1, (), stats)
                download.assert_not_called()
                self.assertEqual(stats["verified_cache_hits"], 1)
                self.assertEqual((root / "snapshot" / entry["path"]).read_bytes(), payload)
                cached.write_bytes(b"corrupted")
                download.side_effect = lambda entry, dest, *rest: dest.write_bytes(payload)
                runner.prepare_inputs({}, runner.fw.BASE, inputs, cache, root / "recovered", 1, (), stats)
                download.assert_called_once()
                self.assertEqual(stats["verified_cache_hits"], 1)
                self.assertEqual((root / "recovered" / entry["path"]).read_bytes(), payload)

    def test_interrupted_download_discards_partial_and_retains_existing_cache(self):
        payload = b"synthetic dependency"
        entry = {"path": "src/example/archive.tar.gz", "source": "https://example.invalid/archive.tar.gz",
                 "version": "fixture", "sha256": hashlib.sha256(payload).hexdigest()}
        class InterruptedResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return entry["source"]
            def read(self, size): raise OSError("synthetic interruption")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / entry["sha256"]
            dest.write_bytes(b"retained")
            with patch.object(runner.fw, "read_inventory", return_value={"files": [entry]}), \
                    patch.object(runner.urllib.request, "urlopen", return_value=InterruptedResponse()):
                with self.assertRaises(OSError):
                    runner.approved_download(entry, dest, 1, (), {"downloaded_bytes": 0})
            self.assertEqual(dest.read_bytes(), b"retained")
            self.assertEqual(list(Path(tmp).iterdir()), [dest])

    def test_interrupted_checkpoint_write_is_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            runner.atomic_json(path, {"retained": True})
            with patch.object(runner.os, "replace", side_effect=OSError("synthetic interruption")):
                with self.assertRaises(OSError):
                    runner.atomic_json(path, {"retained": False})
            self.assertEqual(json.loads(path.read_text()), {"retained": True})
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_windows_execution_fails_closed_before_input_access(self):
        with patch.object(runner.sys, "platform", "win32"):
            with self.assertRaisesRegex(runner.fw.Blocked, "WSL2 Linux required"):
                runner.run(SimpleNamespace(), {})


if __name__ == "__main__":
    unittest.main()
