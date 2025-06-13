import pytest

from database import TEST_DATABASE_NAME, MongoClient


@pytest.fixture(autouse=True, scope="session")
def _drop_test_database() -> None:
    MongoClient().drop_database(TEST_DATABASE_NAME)
