from collections.abc import Sequence
from typing import Any, ClassVar, Self

from pydantic import BaseModel
from pymongo import MongoClient as DefaultMongoClient
from pymongo import ReplaceOne
from pymongo.collection import BulkWriteResult, Collection
from scrapy.utils.project import get_project_settings

DATABASE_NAME = "techtrendstat"
TEST_DATABASE_NAME = "test"


class MongoClient(DefaultMongoClient):
    collection: Collection
    collection_name: str
    indexes: ClassVar[list[tuple[str, int]]]

    settings = get_project_settings()

    def __init__(self, **kwargs: Any) -> None:
        if self.settings["IS_TEST"]:
            super().__init__(
                host=self.settings["MONGODB_HOST"],
                port=self.settings["MONGODB_PORT"],
                username=self.settings["MONGODB_USERNAME"],
                password=self.settings["MONGODB_PASSWORD"],
                **kwargs,
            )
        else:
            if (
                not self.settings["MONGODB_USERNAME"]
                or not self.settings["MONGODB_PASSWORD"]
                or not self.settings["MONGODB_CLUSTER_HOST"]
            ):
                raise ValueError("`username`, `password`, and `cluster_host` are required in a production environment.")

            kwargs = kwargs | {
                "host": f"mongodb+srv://{self.settings['MONGODB_USERNAME']}:{self.settings['MONGODB_PASSWORD']}"
                f"@{self.settings['MONGODB_CLUSTER_HOST']}.mongodb.net/"
            }
            super().__init__(**kwargs)

    def __enter__(self) -> Self:
        super().__enter__()
        self.collection = self.get_database(self.database_name)[self.collection_name]
        self.collection.create_index(self.indexes, unique=True)
        return self

    @property
    def database_name(self) -> str:
        """The `TEST_DATABASE_NAME` value is used if `IS_TEST` environment variable it True."""
        return TEST_DATABASE_NAME if self.settings["IS_TEST"] else getattr(self, "_database_name", DATABASE_NAME)

    @database_name.setter
    def database_name(self, value: str) -> None:
        self._database_name = value

    def bulk_upsert(
        self,
        filter_fields: tuple[str, ...],
        *,
        items: Sequence[BaseModel],
        bulk_write_kwargs: dict[str, Any] | None = None,
        update_one_kwargs: dict[str, Any] | None = None,
    ) -> BulkWriteResult:
        update_one_kwargs = {"upsert": True} | update_one_kwargs if update_one_kwargs else {"upsert": True}
        items_to_upsert = []
        for item in items:
            dumped_model = item.model_dump(mode="json", exclude_none=True)
            filter_ = {field: dumped_model[field] for field in filter_fields}
            items_to_upsert.append(ReplaceOne(filter_, dumped_model, **update_one_kwargs))
        return self.collection.bulk_write(items_to_upsert, **bulk_write_kwargs or {})
