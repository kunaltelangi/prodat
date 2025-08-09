"""
Tests for CodeDriver
"""
import unittest
from prodat.core.controller.code.driver import CodeDriver

class TestCodeDriver(unittest.TestCase):
    def test_init(self):
        failed = False
        try:
            self.code_driver = CodeDriver()
        except TypeError:
            failed = True
        assert failed
