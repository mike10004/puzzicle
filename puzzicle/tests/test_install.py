#!/usr/bin/env python3
import glob
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase


class InstallTest(TestCase):

    def _assert_clean(self, proc: subprocess.CompletedProcess):
        if proc.returncode != 0:
            self.fail(f"exit code {proc.returncode}:\n{proc.stderr}")

    def test_install(self):
        with tempfile.TemporaryDirectory(prefix="puzzicle_") as tempdir:
            venv_dir = Path(tempdir) / "venv"
            self._assert_clean(subprocess.run(["python3", "-m", "venv", venv_dir], capture_output=True, text=True))
            py = venv_dir / "bin" / "python"
            repo_dir = Path(__file__).absolute().parent.parent.parent
            self._assert_clean(subprocess.run([py, "-m", "pip", "install", repo_dir], capture_output=True, text=True))
            puzzicle_package_dir = Path(glob.glob(os.path.join(str(venv_dir), "lib", "python*", "site-packages", "puzzicle"))[0])
            puzzicle_init_file = puzzicle_package_dir / "__init__.py"
            self.assertTrue(puzzicle_init_file.is_file(), f"not a file: {puzzicle_init_file}")
            tests_init_file = puzzicle_package_dir / "tests" / "__init__.py"
            self.assertFalse(tests_init_file.exists(), f"should not exist: {tests_init_file}")
