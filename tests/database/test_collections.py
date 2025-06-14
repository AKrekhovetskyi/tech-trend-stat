from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from database import CollectionVacancies
from tests.conftest import CATEGORY


class TestCollectionVacancies:
    @pytest.mark.usefixtures("_upsert_vacancies_to_collection")
    def test_fetch_vacancies(self) -> None:
        tzinfo = ZoneInfo("Europe/Kyiv")
        end_date_of_publication = datetime(2025, 6, 13, tzinfo=tzinfo)
        with CollectionVacancies() as collection_vacancies:
            assert collection_vacancies.fetch_vacancies(
                CATEGORY,
                start_from_publication_date=end_date_of_publication - timedelta(days=30),
                end_date_of_publication=end_date_of_publication,
            )
