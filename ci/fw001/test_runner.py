import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("runner", Path(__file__).with_name("run.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def test_container_limits_and_existing_isolation(self):
        with patch.object(runner.os, "sched_getaffinity", return_value=set(range(8))):
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


if __name__ == "__main__":
    unittest.main()
