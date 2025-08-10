from typing import Any, Dict, List, Optional

from prodat.core.util.i18n import get as __
from prodat.cli.command.project import ProjectCommand
from prodat.core.util.misc_functions import mutually_exclusive
from prodat.cli.driver.helper import Helper
from prodat.core.controller.task import TaskController


class WorkspaceCommand(ProjectCommand):
    """CLI workspace helpers (notebook, jupyterlab, terminal, rstudio)."""

    def __init__(self, cli_helper: Any):
        super(WorkspaceCommand, self).__init__(cli_helper)

    def _prepare_snapshot(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build snapshot_dict and enforce mutually exclusive environment args
        if one of them is present in kwargs.
        """
        snapshot_dict: Dict[str, Any] = {}
        if kwargs.get("environment_id") or kwargs.get("environment_paths"):
            mutually_exclusive_args = ["environment_id", "environment_paths"]
            mutually_exclusive(mutually_exclusive_args, kwargs, snapshot_dict)
        return snapshot_dict

    def _run_workspace(
        self,
        task_dict: Dict[str, Any],
        snapshot_dict: Dict[str, Any],
        msg_key: str,
        data_paths: Optional[List[str]] = None,
    ) -> Any:
        """
        Echo a translated info message and run the task via task_run_helper.
        Returns whatever task_run_helper returns.
        """
        self.cli_helper.echo(__("info", msg_key))
        return self.task_run_helper(task_dict, snapshot_dict, msg_key, data_paths=data_paths or [])

    @Helper.notify_environment_active(TaskController)
    @Helper.notify_no_project_found
    def notebook(self, **kwargs: Any) -> Any:
        """Launch a Jupyter Notebook workspace."""
        # Inform user
        self.cli_helper.echo(__("info", "cli.workspace.notebook"))

        snapshot_dict = self._prepare_snapshot(kwargs)

        # Validate mem_limit is provided (preserves earlier requirement)
        mem_limit = kwargs.get("mem_limit")
        if mem_limit is None:
            self.cli_helper.echo(__("error", "cli.workspace.error.missing_mem_limit"))
            raise ValueError("mem_limit is required for launching a workspace")

        task_dict = {
            "ports": ["8888:8888"],
            "command_list": ["jupyter", "notebook", "--allow-root"],
            "mem_limit": mem_limit,
            "workspace": "notebook",
        }

        data_paths = kwargs.get("data", [])
        self.cli_helper.echo(__("info", "cli.workspace.run.notebook"))
        return self._run_workspace(task_dict, snapshot_dict, "cli.workspace.notebook", data_paths=data_paths)

    @Helper.notify_environment_active(TaskController)
    @Helper.notify_no_project_found
    def jupyterlab(self, **kwargs: Any) -> Any:
        """Launch a JupyterLab workspace."""
        self.cli_helper.echo(__("info", "cli.workspace.jupyterlab"))

        snapshot_dict = self._prepare_snapshot(kwargs)

        mem_limit = kwargs.get("mem_limit")
        if mem_limit is None:
            self.cli_helper.echo(__("error", "cli.workspace.error.missing_mem_limit"))
            raise ValueError("mem_limit is required for launching a workspace")

        task_dict = {
            "ports": ["8888:8888"],
            "command_list": ["jupyter", "lab", "--allow-root"],
            "mem_limit": mem_limit,
            "workspace": "jupyterlab",
        }

        data_paths = kwargs.get("data", [])
        self.cli_helper.echo(__("info", "cli.workspace.run.jupyterlab"))
        return self._run_workspace(task_dict, snapshot_dict, "cli.workspace.jupyterlab", data_paths=data_paths)

    @Helper.notify_environment_active(TaskController)
    @Helper.notify_no_project_found
    def terminal(self, **kwargs: Any) -> Any:
        """Start an interactive terminal in the workspace."""
        self.cli_helper.echo(__("info", "cli.workspace.terminal"))

        snapshot_dict = self._prepare_snapshot(kwargs)

        mem_limit = kwargs.get("mem_limit")
        if mem_limit is None:
            self.cli_helper.echo(__("error", "cli.workspace.error.missing_mem_limit"))
            raise ValueError("mem_limit is required for launching a workspace")

        task_dict = {
            "interactive": True,
            "ports": kwargs.get("ports", []),
            "mem_limit": mem_limit,
            "command_list": ["/bin/bash"],
        }

        data_paths = kwargs.get("data", [])
        # terminal doesn't echo an extra run message in original, but keep consistency
        return self._run_workspace(task_dict, snapshot_dict, "cli.workspace.terminal", data_paths=data_paths)

    @Helper.notify_environment_active(TaskController)
    @Helper.notify_no_project_found
    def rstudio(self, **kwargs: Any) -> Any:
        """Launch an RStudio server workspace."""
        self.cli_helper.echo(__("info", "cli.workspace.rstudio"))

        snapshot_dict = self._prepare_snapshot(kwargs)

        mem_limit = kwargs.get("mem_limit")
        if mem_limit is None:
            self.cli_helper.echo(__("error", "cli.workspace.error.missing_mem_limit"))
            raise ValueError("mem_limit is required for launching a workspace")

        task_dict = {
            "ports": ["8787:8787"],
            "command_list": [
                "/usr/lib/rstudio-server/bin/rserver",
                "--server-daemonize=0",
                "--server-app-armor-enabled=0",
            ],
            "mem_limit": mem_limit,
            "workspace": "rstudio",
        }

        data_paths = kwargs.get("data", [])
        self.cli_helper.echo(__("info", "cli.workspace.run.rstudio"))
        return self._run_workspace(task_dict, snapshot_dict, "cli.workspace.rstudio", data_paths=data_paths)
