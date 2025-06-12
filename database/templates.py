from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING, ReplaceOne
from pymongo.collection import Collection as DefaultCollection
from scrapy.utils.project import get_project_settings

from database.client import MongoClientSingleton


class Collection:
    """Collection template for inheritance.

    NOTE: Do not forget to close the client after calling
    the `connect_collection` method.
    """

    collection: str
    database: str
    indexes: ClassVar[list[tuple[str, int]]]
    client: MongoClientSingleton

    settings = get_project_settings()

    def connect_collection(self) -> DefaultCollection:
        self.client = MongoClientSingleton(
            is_test=self.settings["IS_TEST"],
            cluster_host=self.settings["MONGODB_CLUSTER_HOST"],
            host=self.settings["MONGODB_HOST"],
            port=self.settings["MONGODB_PORT"],
            username=self.settings["MONGODB_USERNAME"],
            password=self.settings["MONGODB_PASSWORD"],
        )
        collection = self.client[self.database][self.collection]
        collection.create_index(self.indexes, unique=True)
        return collection

    def create_replacements(self, items: list[BaseModel]) -> list[ReplaceOne]:
        """Request replacements for `bulk_write` operation."""
        index_fields = [index[0] for index in self.indexes]
        replacements = []
        for item in items:
            dumped_item = item.model_dump(mode="json")
            indexes = {index: dumped_item[index] for index in index_fields}
            replacements.append(ReplaceOne(indexes, dumped_item, upsert=True))
        return replacements


class CollectionVacancies(Collection):
    database = "vacancy_statistics"
    collection = "vacancies"
    indexes: ClassVar[list[tuple[str, int]]] = [
        ("category", ASCENDING),
        ("publication_date", DESCENDING),
        ("years_of_experience", ASCENDING),
    ]

    def fetch_vacancies(
        self,
        category: str,
        from_datetime: timedelta,
        to_datetime: timedelta,
    ) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        with self.client[self.database][self.collection].aggregate(
            [
                {
                    "$match": {
                        "$and": [
                            {"category": category},
                            {"publication_date": {"$lte": now - to_datetime}},
                            {"publication_date": {"$gte": now - from_datetime}},
                        ]
                    }
                }
            ],
        ) as vacancies:
            return list(vacancies)


class CollectionStatistics(Collection):
    database = "vacancy_statistics"
    collection = "statistics"
    indexes: ClassVar[list[tuple[str, int]]] = [("category", ASCENDING), ("technology_frequency", ASCENDING)]
