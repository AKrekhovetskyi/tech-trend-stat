import csv
import logging
import re
from collections import Counter
from datetime import datetime, timedelta
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

    def __init__(
        self,
        category: str,
        start_from_publication_date: datetime | None = None,
        end_date_of_publication: datetime | None = None,
        extra_text_filters: set[str] | None = None,
    ) -> None:
        """If the `text` is not passed, it will be retrieved from the
        vacancies in MongoDB.
        """
        super().__init__(__class__.__name__)
        self._text: str
        self._category = category
        self._extra_filters = extra_text_filters or set()
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        self.start_from_publication_date = start_from_publication_date or now - timedelta(days=30)
        self.end_date_of_publication = end_date_of_publication or now
        self.logger.debug(
            "start_from_publication_date=%s, end_date_of_publication<=%s",
            self.start_from_publication_date,
            self.end_date_of_publication,
        )

        common_words = (STOPWORDS_DIR / "common-words.json").read_text()
        stopwords = (STOPWORDS_DIR / "stopwords.json").read_text()
        ukr_stopwords = (STOPWORDS_DIR / "ukrainian-stopwords.json").read_text()
        self._stopwords = set(loads(ukr_stopwords) + loads(common_words) + loads(stopwords))

    def _clean_text(self) -> None:
        self.logger.debug("Cleaning text ...")
        # Cyrillic Unicode range: \u0400-\u04FF
        self._text = re.sub(r"[\u0400-\u04FF]+", "", self._text)
        # Get rid of HTML tags and extra symbols.
        to_filter = {"<br>", "<b>", "</b>", "• ", "- ", "\n"}.union(self._extra_filters)
        pattern = re.compile(rf"{'|'.join(to_filter)}", flags=re.IGNORECASE)
        self._text = re.sub(pattern, " ", self._text)
        # Remove any punctuation.
        punctuation_pattern = re.compile(f"[{re.escape('!"#$%&\'()*+,.:;<=>?@[\\]^_`{|}~')}]")
        self._text = punctuation_pattern.sub(" ", self._text)
        # Remove any extra spaces.
        self._text = re.sub(r"\s+", " ", self._text).strip()
        self.logger.debug("Text cleaned")

    def extract_text_from_vacancies(self, path_to_csv: Path | None = None) -> None:
        """Extract vacancy descriptions from a MongoDB collection if no `path_to_csv` argument provided."""
        if not path_to_csv:
            with CollectionVacancies() as collection_vacancies:
                vacancies = collection_vacancies.fetch_vacancies(
                    self._category, self.start_from_publication_date, self.end_date_of_publication
                )
                self._text = " ".join([vacancy["description"] for vacancy in vacancies])
        else:
            with path_to_csv.open() as csv_file:
                reader = csv.DictReader(csv_file)
                self._text = ""
                for row in reader:
                    publication_date = datetime.fromisoformat(row["publication_date"])
                    if (
                        publication_date >= self.start_from_publication_date
                        and publication_date <= self.end_date_of_publication
                        and self._category == row["category"]
                    ):
                        self._text += row["description"]
        self.logger.debug("Text extracted")

    def calculate_frequency_distribution(self, limit_results: int = 20) -> Statistics:
        self._clean_text()

        self.logger.debug("Calculating frequency distribution ...")
        nlp = spacy.load("en_core_web_md")  # Load the spaCy model.
        doc = nlp(self._text)  # Process the text with spaCy.

        # Unicode ranges for English letters.
        eng_uppercase, eng_lowercase = range(65, 90), range(97, 122)

        proper_nouns, lower_to_upper = [], {}
        for token in doc:
            token_text = token.text
            token_text_lower = token_text.lower()
            if (
                token_text_lower not in self._stopwords
                and token_text[0].upper() == token_text[0]
                and (ord(token_text[0]) in eng_uppercase or ord(token_text[0]) in eng_lowercase)
            ):
                proper_nouns.append(token_text_lower)
                lower_to_upper[token_text_lower] = token_text

        proper_nouns_count = Counter(proper_nouns)
        self.logger.debug("Calculation complete")
        return Statistics(
            category=self._category,
            from_datetime=self.start_from_publication_date,
            to_datetime=self.end_date_of_publication,
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
        with file.open("a") as fp:
            fieldnames = Statistics.model_fields.keys()
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            return writer.writerow(statistics.model_dump())


if __name__ == "__main__":
    CATEGORY = "Python"
    wrangler = Wrangler(CATEGORY)
    wrangler.extract_text_from_vacancies()
    statistics = wrangler.calculate_frequency_distribution()
    wrangler.save_statistics(statistics)
