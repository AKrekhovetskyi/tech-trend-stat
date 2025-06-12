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
                {"$addFields": {"pubDate": {"$dateFromString": {"dateString": "$publication_date"}}}},
                {"$match": {"category": category, "pubDate": {"$gte": now - from_datetime, "$lte": now - to_datetime}}},
                {"$project": {"pubDate": 0}},
            ]
        ) as vacancies:
            return list(vacancies)


class CollectionStatistics(MongoClient):
    collection_name = "statistics"
    database_name = "vacancy_statistics"
    indexes: ClassVar[list[tuple[str, int]]] = [("category", ASCENDING), ("technology_frequency", ASCENDING)]
