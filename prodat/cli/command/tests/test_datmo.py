"""
Tests for Project Commands
"""

# TODO: include builtin libraries for the appropriate Python
# try:
#     import __builtin__
# except ImportError:
#     # Python 3
#     import builtins as __builtin__

import os
import tempfile
import platform

from prodat.config import Config
from prodat.cli.driver.helper import Helper
from prodat.cli.command.prodat_command import prodatCommand

class Testprodat():
    def setup_class(self):
        # provide mountable tmp directory for docker
        tempfile.tempdir = "/tmp" if not platform.system(
        ) == "Windows" else None
        test_prodat_dir = os.environ.get('TEST_prodat_DIR',
                                        tempfile.gettempdir())
        self.temp_dir = tempfile.mkdtemp(dir=test_prodat_dir)
        Config().set_home(self.temp_dir)
        self.cli = Helper()

    def teardown_class(self):
        pass

    def test_prodat_base(self):
        base = prodatCommand(self.cli)
        base.parse([])
        assert base.execute()

    def test_prodat_help(self):
        base = prodatCommand(self.cli)
        base.parse(["--help"])
        assert base.execute()
