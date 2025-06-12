from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from pymongo import ASCENDING, DESCENDING

from .client import MongoClient


class CollectionVacancies(MongoClient):
    collection_name = "vacancies"
    database_name = "vacancy_statistics"
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
        with self.collection.aggregate(
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


class CollectionStatistics(MongoClient):
    collection_name = "statistics"
    database_name = "vacancy_statistics"
    indexes: ClassVar[list[tuple[str, int]]] = [("category", ASCENDING), ("technology_frequency", ASCENDING)]
