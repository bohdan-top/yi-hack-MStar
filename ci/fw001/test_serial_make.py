import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import test_runner


class SerialMakeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('make'), 'GNU make required')
    def test_unordered_library_producer_completes_before_consumer(self):
        # Same missing-dependency pattern as pristine rRTSPServer's all target.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Makefile').write_text('all: producer consumer\nproducer:\n\tmkdir -p lib\n\tprintf archive > lib/libtest.a\nconsumer: lib/libtest.a\n\ttest -s lib/libtest.a\n')
            with patch.object(test_runner.runner.os, 'sched_getaffinity', return_value=set(range(6)), create=True), \
                    patch.object(test_runner.runner.os, 'getuid', return_value=0, create=True), \
                    patch.object(test_runner.runner.os, 'getgid', return_value=0, create=True):
                args = test_runner.runner.fw.docker_args('image', '/inputs', '/work', 6, 8)
            makeflags = next(x.split('=', 1)[1] for x in args if x.startswith('MAKEFLAGS='))
            self.assertEqual(makeflags, '-j1')
            process = subprocess.run(['make'], cwd=root, env={**os.environ, 'MAKEFLAGS': makeflags}, capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
