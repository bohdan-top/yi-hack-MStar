import copy
import hashlib
import importlib.util
import pathlib
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("build", pathlib.Path(__file__).with_name("manual-build.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class Bootstrap(unittest.TestCase):
    def fixture(self, inputs):
        lock = copy.deepcopy(build.read_inventory())
        lock["review_status"] = "approved"
        lock["image_id"] = "sha256:" + "a" * 64
        for item in lock["files"]:
            p = inputs / item["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(item["path"].encode())
            item["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            item["version"] = "synthetic-fixture"
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

    def test_isolation_command(self):
        args = build.docker_args("sha256:" + "a" * 64, "/private/inputs", "/private/work")
        for token in ("--network=none", "--pull=never", "--read-only", "--cap-drop=ALL",
                      "--security-opt=no-new-privileges", "--log-driver=none"):
            self.assertIn(token, args)
        self.assertNotIn("--privileged", args)


if __name__ == "__main__":
    unittest.main()
