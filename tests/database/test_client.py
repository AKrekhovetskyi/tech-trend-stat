from faker import Faker
from pymongo import ASCENDING

from database import MongoClient, VacancyItem


class TestMongoClient:
    def test_bulk_upsert(self, vacancy_items: list[VacancyItem], faker: Faker) -> None:
        mongo_client = MongoClient
        mongo_client.collection_name = faker.pystr()
        mongo_client.indexes = [("url", ASCENDING)]
        with mongo_client() as client:
            # Use `url` field as it's unique and all documents will be upserted.
            session = client.start_session()
            client.bulk_upsert(
                ("url",),
                items=vacancy_items,
                bulk_write_kwargs={"session": session},
                update_one_kwargs={"sort": {"url": ASCENDING}},
            )
            assert client.collection.count_documents({}) > 1
