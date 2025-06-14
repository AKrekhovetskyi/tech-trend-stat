import csv
from pathlib import Path

import pytest

from database import TEST_DATABASE_NAME, CollectionVacancies, MongoClient, VacancyItem

CATEGORY = "Python"


@pytest.fixture(autouse=True, scope="session")
def _drop_test_database() -> None:
    MongoClient().drop_database(TEST_DATABASE_NAME)


@pytest.fixture(scope="session")
def test_vacancies() -> Path:
    return Path(__file__).parent / "test_vacancies.csv"


@pytest.fixture(scope="session")
def vacancy_items(test_vacancies: Path) -> list[VacancyItem]:
    with test_vacancies.open() as csv_file:
        reader = csv.DictReader(csv_file)
        return [VacancyItem(**item) for item in reader]  # type: ignore[reportArgumentType]


@pytest.fixture
def _upsert_vacancies_to_collection(vacancy_items: list[VacancyItem]) -> None:
    with CollectionVacancies() as collection_vacancies:
        collection_vacancies.bulk_upsert(("url",), items=vacancy_items)
