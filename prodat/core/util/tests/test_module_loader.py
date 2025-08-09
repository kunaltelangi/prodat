"""
Tests for __init__.py
"""

from prodat.core.util import get_class_contructor

class TestModuleLoader():
    def test_loader(self):
        constructor = get_class_contructor(
            'prodat.core.util.exceptions.InvalidProjectPath')
        loaded = constructor()
        assert loaded
