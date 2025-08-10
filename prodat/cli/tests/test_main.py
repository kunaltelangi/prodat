import os
import tempfile
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

from prodat.core.util.misc_functions import pytest_docker_environment_failed_instantiation

tempfile.tempdir = "/tmp" if platform.system() != "Windows" else None
test_prodat_dir = os.environ.get("TEST_prodat_DIR", tempfile.gettempdir())


def to_bytes(val: Union[str, bytes, bytearray]) -> bytes:
    if isinstance(val, (bytes, bytearray)):
        return bytes(val)
    if isinstance(val, str):
        return val.encode("utf-8")
    return str(val).encode("utf-8")


class TestMain:
    @classmethod
    def setup_class(cls) -> None:
        """Create a clean temporary directory and a minimal project structure for tests."""
        cls.temp_dir = Path(tempfile.mkdtemp(dir=test_prodat_dir))
        cls.execpath = "prodat"
        # remember cwd so we can restore later if needed
        cls._old_cwd = Path.cwd()
        os.chdir(cls.temp_dir)

        # Create environment_driver definition (Dockerfile)
        cls.env_def_path = cls.temp_dir / "Dockerfile"
        cls.env_def_path.write_bytes(to_bytes("FROM python:3.5-alpine\n"))

        # Create config file
        cls.config_filepath = cls.temp_dir / "config.json"
        cls.config_filepath.write_bytes(to_bytes("{}"))

        # Create stats file
        cls.stats_filepath = cls.temp_dir / "stats.json"
        cls.stats_filepath.write_bytes(to_bytes("{}"))

        # Create test file
        cls.filepath = cls.temp_dir / "file.txt"
        cls.filepath.write_bytes(to_bytes("test"))

        # Create script file
        cls.script_filepath = cls.temp_dir / "script.py"
        cls.script_filepath.write_bytes(to_bytes('print("hello")'))

    def run_command(
        self,
        command: Iterable[str],
        input_text: Optional[str] = None,
        timeout: int = 15,
    ) -> Tuple[str, str, int]:
        """
        Run a command in the test temp directory and return (stdout, stderr, returncode).
        Uses subprocess.run to avoid hangs; returns decoded strings.
        """
        try:
            completed = subprocess.run(
                list(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.temp_dir,
                input=input_text,
                timeout=timeout,
                text=True,  # decode to str
            )
            return completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired as e:
            # Return what we have if timeout
            return getattr(e, "stdout", "") or "", getattr(e, "stderr", "") or "", 124

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up temporary directory and restore working dir."""
        try:
            os.chdir(cls._old_cwd)
        except Exception:
            pass
        try:
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_version(self) -> None:
        """`prodat version` should print a line containing 'prodat version:' and not produce stderr."""
        success = True
        try:
            out, err, rc = self.run_command([self.execpath, "version"])
            if rc != 0:
                success = False
            elif err:
                success = False
            elif "prodat version:" not in out:
                success = False
        except Exception:
            success = False
        assert success

    def test_init(self) -> None:
        """
        `prodat init --name test --description test` should print 'Initializing project'.
        Note: do not include shell-style quotes in the argument values.
        """
        success = True
        try:
            # pass name/description as plain strings (no extra quoting)
            out, err, rc = self.run_command(
                [self.execpath, "init", "--name", "test", "--description", "test"],
                input_text="\n",  # if the command waits for confirmation / newline
            )
            if rc != 0:
                success = False
            elif err:
                success = False
            elif "Initializing project" not in out:
                success = False
        except Exception:
            success = False
        assert success

    # Uncomment / enable when Docker environment is available and desired
    # @pytest_docker_environment_failed_instantiation(test_prodat_dir)
    # def test_run(self):
    #     try:
    #         success = True
    #         out, err, rc = self.run_command([self.execpath, "run", "python script.py"])
    #         if rc != 0:
    #             success = False
    #         elif err:
    #             success = False
    #         elif 'hello' not in out:
    #             success = False
    #     except Exception:
    #         success = False
    #     assert success

    def test_run_ls(self) -> None:
        """`prodat ls` should produce output containing 'id' and no stderr."""
        success = True
        try:
            out, err, rc = self.run_command([self.execpath, "ls"])
            if rc != 0:
                success = False
            elif err:
                success = False
            elif "id" not in out:
                success = False
        except Exception:
            success = False
        assert success

    def test_snapshot_create(self) -> None:
        """`prodat snapshot create -m message` should print a Created message."""
        success = True
        try:
            out, err, rc = self.run_command([self.execpath, "snapshot", "create", "-m", "message"])
            if rc != 0:
                success = False
            elif err:
                success = False
            elif "Created snapshot with id" not in out:
                success = False
        except Exception:
            success = False
        assert success

    def test_snapshot_ls(self) -> None:
        """`prodat snapshot ls` should return a listing containing 'id'."""
        success = True
        try:
            out, err, rc = self.run_command([self.execpath, "snapshot", "ls"])
            if rc != 0:
                success = False
            elif err:
                success = False
            elif "id" not in out:
                success = False
        except Exception:
            success = False
        assert success
