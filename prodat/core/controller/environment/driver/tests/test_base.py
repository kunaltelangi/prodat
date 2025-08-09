"""
Tests for EnvironmentDriver
"""

import unittest
from prodat.core.controller.environment.driver import EnvironmentDriver

class TestEnvironmentDriver(unittest.TestCase):
    def test_init(self):
        failed = False
        try:
            self.environment_driver = EnvironmentDriver()
        except TypeError:
            failed = True
        assert failed
