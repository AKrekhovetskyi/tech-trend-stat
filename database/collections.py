from datetime import datetime
from typing import Any, ClassVar

from pymongo import ASCENDING, DESCENDING

from .client import MongoClient


class CollectionVacancies(MongoClient):
    collection_name = "vacancies"
    indexes: ClassVar[list[tuple[str, int]]] = [
        ("category", ASCENDING),
        ("publication_date", DESCENDING),
        ("years_of_experience", ASCENDING),
    ]

    def fetch_vacancies(
        self, category: str, start_from_publication_date: datetime, end_date_of_publication: datetime
    ) -> list[dict[str, Any]]:
        with self.collection.aggregate(
            [
                {"$addFields": {"pubDate": {"$dateFromString": {"dateString": "$publication_date"}}}},
                {
                    "$match": {
                        "category": category,
                        "pubDate": {"$gte": start_from_publication_date, "$lte": end_date_of_publication},
                    }
                },
                {"$project": {"pubDate": 0}},
            ]
        ) as vacancies:
            return list(vacancies)


class CollectionStatistics(MongoClient):
    collection_name = "statistics"
    indexes: ClassVar[list[tuple[str, int]]] = [("category", ASCENDING), ("upsert_datetime", DESCENDING)]
