import csv
from pathlib import Path

import pytest
from faker import Faker

from database import CollectionStatistics, CollectionVacancies, Statistics, VacancyItem
from techtrendanalysis.wrangler import Wrangler

CATEGORY = "Python"


class TestWrangler:
    path_to_csv = Path(__file__).parent / "test_vacancies.csv"

    @pytest.fixture(scope="module")
    def vacancy_items(self) -> list[VacancyItem]:
        with self.path_to_csv.open() as csv_file:
            reader = csv.DictReader(csv_file)
            return [VacancyItem(**item) for item in reader]  # type: ignore[reportArgumentType]

    @pytest.fixture
    def _upsert_vacancies_to_collection(self, vacancy_items: list[VacancyItem]) -> None:
        with CollectionVacancies() as collection_vacancies:
            collection_vacancies.bulk_upsert(("url",), items=vacancy_items)  # type: ignore[reportArgumentType]

    @pytest.fixture
    def wrangler(self) -> Wrangler:
        return Wrangler(CATEGORY)

    def test__clean_text(self, wrangler: Wrangler) -> None:
        wrangler._text = (
            "• Від 5 років досвіду <b>бекенд-розробки на Python</b>; "
            "<br>• Професійний досвід у розробці та реалізації RESTful API; "  # noqa: RUF001
            "- Знання реляційних баз даних (MySQL, PostgreSQL);\n "
            "Solid knowledge of relational databases (MySQL, PostgreSQL, SP-API); "
            "Proficiency in graph databases (especially Amazon Neptune); "
            "Strong skills in JSON/XML"
        )
        wrangler._clean_text()
        cleaned_text = (
            "5 Python RESTful API MySQL PostgreSQL "
            "Solid knowledge of relational databases MySQL PostgreSQL SP-API "
            "Proficiency in graph databases especially Amazon Neptune "
            "Strong skills in JSON/XML"
        )
        assert wrangler._text == cleaned_text, f"{wrangler._text=}"

    @pytest.mark.usefixtures("_upsert_vacancies_to_collection")
    def test_extract_text_from_vacancies(self, wrangler: Wrangler) -> None:
        wrangler.extract_text_from_vacancies(path_to_csv=self.path_to_csv)
        assert wrangler._text

        wrangler._text = ""
        wrangler.extract_text_from_vacancies()
        assert wrangler._text

    def test_calculate_frequency_distribution(self, wrangler: Wrangler, vacancy_items: list[VacancyItem]) -> None:
        wrangler._text = " ".join([vacancy.description for vacancy in vacancy_items])
        statistics = wrangler.calculate_frequency_distribution(limit_results=10)
        expected_technology_frequency = {
            "API": 9,
            "Python": 8,
            "Amazon": 5,
            "PostgreSQL": 4,
            "Neptune": 4,
            "DevOps": 4,
            "RESTful": 3,
            "Django": 3,
            "FastAPI": 3,
            "Docker": 3,
        }
        assert statistics.technology_frequency == expected_technology_frequency

    def test_save_statistics(self, wrangler: Wrangler, faker: Faker, tmp_path: Path) -> None:
        statistics = Statistics(
            category=faker.pystr(),
            from_datetime=faker.date_time(),
            to_datetime=faker.date_time(),
            technology_frequency=faker.pydict(value_types=(int,)),
            upsert_datetime=faker.date_time(),
        )
        wrangler.save_statistics(statistics)
        with CollectionStatistics() as collection_statistics:
            assert collection_statistics.collection.count_documents({})

        CollectionStatistics.collection_name = str(tmp_path)
        wrangler.save_statistics(statistics, to_mongodb_collection=False)
        assert Path(f"{tmp_path!s}.csv").exists()
