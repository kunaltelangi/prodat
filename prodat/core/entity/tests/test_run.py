"""
Tests for Run
"""
from prodat.core.entity.task import Task as CoreTask
from prodat.core.entity.run import Run

class TestRun():
    def setup_class(self):
        self.task_dict = {
            "id": "test",
            "model_id": "my_model",
            "command": "python test.py"
        }

    def test_run_object_instantiate(self):
        task_obj = CoreTask(self.task_dict)
        result = Run(task_obj)
        assert result
        assert isinstance(result, Run)