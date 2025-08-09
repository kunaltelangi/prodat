"""
Bring in all of prodat's public python interfaces
"""

import os
from prodat.core.util.logger import prodatLogger
from prodat.config import Config

prodat_root = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(prodat_root, 'VERSION')) as file:
    __version__ = file.read()

# Config is required to run first so it can
# initialize/find prodat home directory (.prodat)
# This is required for logging to place the logs in a
# place for the user.
config = Config()
config.set_home(os.getcwd())

log = prodatLogger.get_logger(__name__)
log.info("handling command %s", config.home)

import prodat.snapshot
import prodat.logger
import prodat.config
