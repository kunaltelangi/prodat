import os
from prodat.core.util.json_store import JSONStore
from prodat.core.util.exceptions import InvalidArgumentType


class Logger:
    """Logger is a class to store properties like configs and results.

    Attributes
    ----------
    task_dir : str
        Path to the task directory

    Methods
    -------
    log_config(config)
        Save the configuration dictionary for the run
    log_result(results)
        Save the results dictionary for the run

    Raises
    ------
    InvalidArgumentType
    """

    def __init__(self, task_dir="/task"):
        self.task_dir = task_dir

    @staticmethod
    def _save_dictionary(dictionary, path):
        json_obj = JSONStore(path)
        data = json_obj.to_dict()
        data.update(dictionary)
        json_obj.to_file(data)
        return data

    def _get_file_path(self, filename):
        base_dir = self.task_dir if os.path.isdir(self.task_dir) else os.getcwd()
        return os.path.join(base_dir, filename)

    def log_config(self, config):
        if not isinstance(config, dict):
            raise InvalidArgumentType()
        return self._save_dictionary(config, self._get_file_path("config.json"))

    def log_result(self, results):
        if not isinstance(results, dict):
            raise InvalidArgumentType()
        return self._save_dictionary(results, self._get_file_path("stats.json"))
