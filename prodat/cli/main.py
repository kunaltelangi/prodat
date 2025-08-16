#!/usr/bin/python

import os
import sys

from prodat.cli.command.base import BaseCommand
from prodat.cli.driver.helper import Helper
from prodat.core.util.exceptions import CLIArgumentError
from prodat.core.util.i18n import get as __
from prodat.core.util.logger import prodatLogger
from prodat.config import Config


def main():
    cli_helper = Helper()

    config = Config()
    config.set_home(os.getcwd())

    log = prodatLogger.get_logger(__name__)
    log.info("handling command %s", config.home)

    command_name = None

    if len(sys.argv) > 1 and sys.argv[1] in cli_helper.get_command_choices():
        cmd = sys.argv[1]

        project_cmds = {
            "init": "project",
            "version": "project",
            "--version": "project",
            "-v": "project",
            "status": "project",
            "cleanup": "project",
            "dashboard": "project",
            "configure": "project",
        }

        workspace_cmds = {"notebook", "jupyterlab", "terminal", "rstudio"}
        run_cmds = {"rerun", "run", "stop", "ls", "delete"}

        if cmd in project_cmds:
            command_name = project_cmds[cmd]
            if cmd in {"version", "--version", "-v", "status", "cleanup", "dashboard", "configure"}:
                sys.argv[1] = cmd
        elif cmd in workspace_cmds:
            command_name = "workspace"
            sys.argv[1] = cmd
        elif cmd in run_cmds:
            command_name = "run"
            if cmd in {"run", "stop"} and len(sys.argv) == 2:
                sys.argv.append("--help")
            sys.argv[1] = cmd
        else:
            command_name = cmd

        command_class = cli_helper.get_command_class(command_name)

    elif len(sys.argv) == 1:
        command_class = cli_helper.get_command_class("prodat_command")
    else:
        command_class = BaseCommand

    try:
        command_instance = command_class(cli_helper)
    except TypeError as ex:
        cli_helper.echo(__("error", "cli.general", f"{type(ex)} {ex}"))
        return 1

    try:
        command_instance.parse(sys.argv[1:])
    except CLIArgumentError as ex:
        cli_helper.echo(__("error", "cli.general", f"{type(ex)} {ex}"))
        return 1

    try:
        command_instance.execute()
        return 0
    except Exception as ex:
        cli_helper.echo(__("error", "cli.general", f"{type(ex)} {ex}"))
        return 1
