import csv
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from json import loads
from pathlib import Path
from typing import Any

import spacy
from pymongo.results import BulkWriteResult

from database import DatabaseStatistics, DatabaseVacancies, Statistics

STOPWORDS_DIR = Path("techtrendanalysis/stopwords")


class Wrangler(DatabaseVacancies):
    """Clean up the provided vacancy text and extract technology statistics."""

    def __init__(
        self,
        text: str | None,
        category: str,
        extra_filters: set[str] | None = None,
    ) -> None:
        """If the `text` is not passed, it will be retrieved from the
        vacancies in MongoDB.
        """
        self._text = text
        self._category = category
        self._extra_filters = extra_filters or set()
        self._from_datetime: timedelta = timedelta(days=0)
        self._to_datetime: timedelta = timedelta(days=0)

        ukr_stopwords = STOPWORDS_DIR / "ukrainian-stopwords.json"
        common_words = STOPWORDS_DIR / "common-words.json"
        self._stopwords = set(loads(ukr_stopwords.read_text()) + loads(common_words.read_text()))

    def _clean_text(self) -> str:
        to_filter = {"<br>", "<b>", "</b>", "• ", "- "}.union(self._extra_filters)
        pattern = re.compile(rf"{'|'.join(to_filter)}", flags=re.IGNORECASE)
        self._text = re.sub(pattern, " ", self._text)

    def extract_text_from_vacancies(
        self,
        from_datetime: timedelta = timedelta(days=30),
        to_datetime: timedelta = timedelta(days=0),
    ) -> None:
        self._from_datetime = from_datetime
        self._to_datetime = to_datetime
        self.connect_collection()
        vacancies = self.fetch_vacancies(self._category, from_datetime, to_datetime)
        self._text = " ".join([vacancy["description"] for vacancy in vacancies])
        self.client.close()

    def calculate_frequency_distribution(self, limit_results: int = 20) -> Statistics:
        if not self._text:
            self.extract_text_from_vacancies()
        self._clean_text()

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
        return Statistics(
            category=self._category,
            from_datetime=now - self._from_datetime,
            to_datetime=now - self._to_datetime,
            technology_frequency={
                lower_to_upper[noun_frequency[0]]: noun_frequency[1]
                for noun_frequency in proper_nouns_count.most_common(limit_results)
            },
        )

    @staticmethod
    def save_statistics(statistics: Statistics, *, to_db: bool = True) -> BulkWriteResult | Any:
        if to_db:
            db = DatabaseStatistics()
            collection = db.connect_collection()
            bulk_write_result = collection.bulk_write(db.create_replacements([statistics]))
            db.client.close()
            return bulk_write_result

        file = Path(f"{DatabaseStatistics.collection}.csv")
        file_exists = file.exists()
        fieldnames = statistics.model_fields.keys()
        with file.open("a") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader() if not file_exists else None
            return writer.writerow(statistics.model_dump())


if __name__ == "__main__":
    CATEGORY = "Python"
    wrangler = Wrangler(None, CATEGORY)
    statistics = wrangler.calculate_frequency_distribution()
    wrangler.save_statistics(statistics)
