from datetime import UTC, datetime, timedelta
from os import getenv
from typing import Any, ClassVar

from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING, ReplaceOne
from pymongo.collection import Collection
from scrapy.utils.project import get_project_settings

from database.client import MongoClientSingleton


class Database:
    """Database template for inheritance.

    NOTE: Do not forget to close the client after calling
    the `connect_collection` method.
    """

    collection: str
    database: str
    indices: ClassVar[list[tuple[str, int]]]
    client: MongoClientSingleton

    settings = get_project_settings()

    def connect_collection(self) -> Collection:
        self.client = MongoClientSingleton(
            is_test=self.settings["IS_TEST"],
            cluster_host=getenv("MONGODB_CLUSTER_HOST"),
            host=getenv("MONGODB_HOST"),
            port=int(port) if (port := getenv("MONGODB_PORT")) else None,
            username=getenv("MONGODB_USERNAME"),
            password=getenv("MONGODB_PASSWORD"),
        )
        collection = self.client[self.database][self.collection]
        collection.create_index(self.indices, unique=True)
        return collection

    def create_replacements(self, items: list[BaseModel]) -> list[ReplaceOne]:
        """Request replacements for `bulk_write` operation."""
        index_fields = [index[0] for index in self.indices]
        replacements = []
        for item in items:
            dumped_item = item.model_dump()
            indices = {index: dumped_item[index] for index in index_fields}
            replacements.append(ReplaceOne(indices, dumped_item, upsert=True))
        return replacements


class DatabaseVacancies(Database):
    database = "vacancy_statistics"
    collection = "vacancies"
    indices: ClassVar[list[tuple[str, int]]] = [
        ("publication_date", DESCENDING),
        ("company_name", ASCENDING),
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


class DatabaseStatistics(Database):
    database = "vacancy_statistics"
    collection = "statistics"
    indices: ClassVar[list[tuple[str, int]]] = [("category", ASCENDING), ("technology_frequency", ASCENDING)]
