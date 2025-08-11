import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from kids.cache import cache

from prodat.core.util.i18n import get as __
from prodat.core.entity.model import Model
from prodat.core.entity.code import Code
from prodat.core.entity.environment import Environment
from prodat.core.entity.file_collection import FileCollection
from prodat.core.entity.task import Task
from prodat.core.entity.snapshot import Snapshot
from prodat.core.entity.user import User
from prodat.core.util.exceptions import (
    InputError,
    EntityNotFound,
    MoreThanOneEntityFound,
    DALNotInitialized,
)
from prodat.core.util.misc_functions import create_unique_hash
from prodat.core.storage.driver.blitzdb_dal_driver import BlitzDBDALDriver


class LocalDAL:
    def __init__(self, driver_type: str, driver_options: Optional[Dict[str, Any]] = None, driver: Any = None):
        self.driver_type = driver_type
        self.driver_options = driver_options or {}
        self.driver = driver
        self._is_initialized = False

    @property
    def is_initialized(self) -> bool:
        if self._is_initialized:
            return True

        conn = self.driver_options.get("connection_string")
        if conn and os.path.isdir(conn):
            if not self.driver and self.driver_type == "blitzdb":
                self.driver = BlitzDBDALDriver(**self.driver_options)
            self._is_initialized = True
            return True

        # If a driver instance was provided directly, consider initialized
        if self.driver is not None:
            self._is_initialized = True
            return True

        self._is_initialized = False
        return False

    def init(self) -> None:
        if self.driver:
            self._is_initialized = True
            return

        if self.driver_type == "blitzdb":
            conn = self.driver_options.get("connection_string")
            if conn and not os.path.isdir(conn):
                # create directory to allow initialization
                os.makedirs(conn, exist_ok=True)
            self.driver = BlitzDBDALDriver(**self.driver_options)
            self._is_initialized = True
            return

        raise DALNotInitialized()

    @property
    def model(self) -> "ModelMethods":
        if not self.is_initialized:
            raise DALNotInitialized()
        return ModelMethods(self.driver)

    @property
    def code(self) -> "CodeMethods":
        if not self.is_initialized:
            raise DALNotInitialized()
        return CodeMethods(self.driver)

    @property
    def environment(self) -> "EnvironmentMethods":
        if not self.is_initialized:
            raise DALNotInitialized()
        return EnvironmentMethods(self.driver)

    @property
    def file_collection(self) -> "FileCollectionMethods":
        if not self.is_initialized:
            raise DALNotInitialized()
        return FileCollectionMethods(self.driver)

    @cache
    @property
    def task(self) -> "TaskMethods":
        if not self.is_initialized:
            raise DALNotInitialized()
        return TaskMethods(self.driver)

    @cache
    @property
    def snapshot(self) -> "SnapshotMethods":
        if not self.is_initialized:
            raise DALNotInitialized()
        return SnapshotMethods(self.driver)

    @cache
    @property
    def user(self) -> "UserMethods":
        if not self.is_initialized:
            raise DALNotInitialized()
        return UserMethods(self.driver)


class EntityMethodsCRUD:
    def __init__(self, collection: str, entity_class: Any, driver: Any):
        self.collection = collection
        self.entity_class = entity_class
        self.driver = driver

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        if hasattr(obj, "to_dictionary"):
            return obj.to_dictionary()
        if isinstance(obj, dict):
            return dict(obj)
        return self.entity_class(obj).to_dictionary()

    def get_by_id(self, entity_id: str) -> Any:
        obj = self.driver.get(self.collection, entity_id)
        if not obj:
            raise EntityNotFound()
        return self.entity_class(obj)

    def get_by_shortened_id(self, shortened_entity_id: str) -> Any:
        obj = self.driver.get_by_shortened_id(self.collection, shortened_entity_id)
        if not obj:
            raise EntityNotFound()
        return self.entity_class(obj)

    def create(self, prodat_entity: Any) -> Any:
        dict_obj = self._to_dict(prodat_entity)

        if "id" not in dict_obj or not dict_obj["id"]:
            dict_obj["id"] = create_unique_hash()

        now = datetime.utcnow()
        dict_obj.setdefault("created_at", now)
        dict_obj["updated_at"] = now

        response = self.driver.set(self.collection, dict_obj)
        if not response:
            raise InputError(__("error", "storage.local.dal.create"))
        return self.entity_class(response)

    def update(self, prodat_entity: Any) -> Any:
        # accept either dict-like or entity instance
        new_dict = self._to_dict(prodat_entity)

        entity_id = new_dict.get("id")
        if not entity_id:
            raise InputError(__("error", "storage.local.dal.update"))

        original = self.get_by_id(entity_id)
        original_dict = original.to_dictionary()

        # merge original and new, preferring new values (including explicit None)
        merged = dict(original_dict)
        for k, v in new_dict.items():
            merged[k] = v

        merged["updated_at"] = datetime.utcnow()
        response = self.driver.set(self.collection, merged)
        if not response:
            raise InputError(__("error", "storage.local.dal.update"))
        return self.entity_class(response)

    def delete(self, entity_id: str) -> bool:
        result = self.driver.delete(self.collection, entity_id)
        if not result:
            # normalize behavior: if deletion had no effect, raise not found
            raise EntityNotFound()
        return True

    def query(self, query_params: Dict[str, Any], sort_key: Optional[str] = None, sort_order: Optional[str] = None) -> List[Any]:
        items = self.driver.query(self.collection, query_params, sort_key, sort_order)
        return [self.entity_class(item) for item in items]

    def findOne(self, query_params: Dict[str, Any]) -> Any:
        results = self.query(query_params)
        if len(results) == 0:
            raise EntityNotFound()
        if len(results) > 1:
            raise MoreThanOneEntityFound()
        return results[0]


class ModelMethods(EntityMethodsCRUD):
    def __init__(self, driver: Any):
        super(ModelMethods, self).__init__("model", Model, driver)


class CodeMethods(EntityMethodsCRUD):
    def __init__(self, driver: Any):
        super(CodeMethods, self).__init__("code", Code, driver)


class EnvironmentMethods(EntityMethodsCRUD):
    def __init__(self, driver: Any):
        super(EnvironmentMethods, self).__init__("environment", Environment, driver)


class FileCollectionMethods(EntityMethodsCRUD):
    def __init__(self, driver: Any):
        super(FileCollectionMethods, self).__init__("file_collection", FileCollection, driver)


class TaskMethods(EntityMethodsCRUD):
    def __init__(self, driver: Any):
        super(TaskMethods, self).__init__("task", Task, driver)


class SnapshotMethods(EntityMethodsCRUD):
    def __init__(self, driver: Any):
        super(SnapshotMethods, self).__init__("snapshot", Snapshot, driver)


class UserMethods(EntityMethodsCRUD):
    def __init__(self, driver: Any):
        super(UserMethods, self).__init__("user", User, driver)
