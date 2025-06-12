import csv
import logging
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from json import loads
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import spacy
from pymongo.results import BulkWriteResult

from database import CollectionStatistics, CollectionVacancies, Statistics

STOPWORDS_DIR = Path("techtrendanalysis/stopwords")


class Logging:
    def __init__(self, name: str = __name__) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        self.logger.addHandler(handler)


class Wrangler(Logging):
    """Clean up the provided vacancy text and extract technology statistics."""

    def __init__(self, category: str, extra_filters: set[str] | None = None) -> None:
        """If the `text` is not passed, it will be retrieved from the
        vacancies in MongoDB.
        """
        super().__init__(__class__.__name__)
        self._text: str
        self._category = category
        self._extra_filters = extra_filters or set()
        self._from_datetime: timedelta
        self._to_datetime: timedelta

        ukr_stopwords = STOPWORDS_DIR / "ukrainian-stopwords.json"
        common_words = STOPWORDS_DIR / "common-words.json"
        self._stopwords = set(loads(ukr_stopwords.read_text()) + loads(common_words.read_text()))

    def _clean_text(self) -> None:
        self.logger.debug("Cleaning text ...")
        to_filter = {"<br>", "<b>", "</b>", "• ", "- "}.union(self._extra_filters)
        pattern = re.compile(rf"{'|'.join(to_filter)}", flags=re.IGNORECASE)
        self._text = re.sub(pattern, " ", self._text)
        self.logger.debug("Text cleaned")

    def extract_text_from_vacancies(
        self,
        *,
        from_datetime: timedelta = timedelta(days=30),
        to_datetime: timedelta = timedelta(days=0),
        from_mongodb_collection: bool = True,
    ) -> None:
        self._from_datetime = from_datetime
        self._to_datetime = to_datetime

        self.logger.debug(
            "Extracting vacancies text in range from_datetime=%s, to_datetime=%s", from_datetime, to_datetime
        )
        if from_mongodb_collection:
            with CollectionVacancies() as collection_vacancies:
                vacancies = collection_vacancies.fetch_vacancies(self._category, from_datetime, to_datetime)
                self._text = " ".join([vacancy["description"] for vacancy in vacancies])
        else:
            now = datetime.now(ZoneInfo("Europe/Kyiv"))
            with Path(f"{CollectionVacancies.collection_name}.csv").open() as csv_file:
                reader = csv.DictReader(csv_file)
                self._text = ""
                for row in reader:
                    publication_date = datetime.fromisoformat(row["publication_date"])
                    if (
                        publication_date >= (now - from_datetime)
                        and publication_date <= (now - to_datetime)
                        and self._category == row["category"]
                    ):
                        self._text += row["description"]
        self.logger.debug("Text extracted")

    def calculate_frequency_distribution(self, limit_results: int = 20) -> Statistics:
        self._clean_text()

        self.logger.debug("Calculating frequency distribution ...")
        nlp = spacy.load("en_core_web_sm")  # Load the spaCy model.
        doc = nlp(self._text)  # Process the text with spaCy.

        # Unicode ranges for English letters.
        eng_uppercase, eng_lowercase = range(65, 90), range(97, 122)

        proper_nouns, lower_to_upper = [], {}
        for token in doc:
            if (
                token.pos_ == "PROPN"  # IT techs are mostly proper nouns.
                and (token_text := token.text) not in self._stopwords
                and (ord(token_text[0]) in eng_uppercase or ord(token_text[0]) in eng_lowercase)
            ):
                proper_nouns.append(token_text.lower())
                lower_to_upper[token_text.lower()] = token_text

        proper_nouns_count = Counter(proper_nouns)
        now = datetime.now(UTC)
        self.logger.debug("Calculation complete")
        return Statistics(
            category=self._category,
            from_datetime=now - self._from_datetime,
            to_datetime=now - self._to_datetime,
            technology_frequency={
                lower_to_upper[noun_frequency[0]]: noun_frequency[1]
                for noun_frequency in proper_nouns_count.most_common(limit_results)
            },
            upsert_datetime=datetime.now(ZoneInfo("Europe/Kyiv")),
        )

    def save_statistics(self, statistics: Statistics, *, to_mongodb_collection: bool = True) -> BulkWriteResult | Any:
        """Save statistics to the MongoDB collection file.
        If `to_mongodb_collection` is False, then the statistics will be saved to a CSV file.
        """
        log_message = f"Saving statistics {to_mongodb_collection=}: {statistics=}"
        self.logger.debug(log_message)
        if to_mongodb_collection:
            with CollectionStatistics() as collection_statistics:
                return collection_statistics.bulk_upsert(("from_datetime", "to_datetime"), items=[statistics])

        file = Path(f"{CollectionStatistics.collection_name}.csv")
        file_exists = file.exists()
        fieldnames = Statistics.model_fields.keys()
        with file.open("a") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader() if not file_exists else None
            return writer.writerow(statistics.model_dump())


if __name__ == "__main__":
    CATEGORY = "Python"
    wrangler = Wrangler(CATEGORY)
    wrangler.extract_text_from_vacancies()
    statistics = wrangler.calculate_frequency_distribution()
    wrangler.save_statistics(statistics)
