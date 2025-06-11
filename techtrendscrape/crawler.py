import csv

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from database import DatabaseVacancies, Statistics
from techtrendanalysis.wrangler import Wrangler


class CrawlToCSV:
    """Crawl vacancies and extract statistics, avoiding usage of MongoDB.

    The class provides a simple interface for quickly getting technology
    statistics. It is intended for overview use.
    """

    def __init__(self, category: str) -> None:
        self._category = category
        self._settings = get_project_settings()
        # Save the results to a CSV file instead of MongoDB.
        self._settings.update(
            {
                "ITEM_PIPELINES": {
                    "techtrendscrape.pipelines.CSVPipeline": 300,
                }
            }
        )

    def start(self) -> None:
        """Scrape vacancies from Djinni by the provided category and save to
        `vacancies.csv` file.
        """
        process = CrawlerProcess(self._settings)
        process.crawl("djinni", categories=self._category)
        process.start()

    def extract_statistics(self, *, save: bool = True) -> Statistics:
        """Merge descriptions from the `vacancies.csv`, extract
        statistics and save it to the `statistics.csv`.
        """
        # Collect vacancy descriptions.
        with open(f"{DatabaseVacancies.collection}.csv") as csv_file:
            reader = csv.DictReader(csv_file)
            descriptions = " ".join([item["description"] for item in reader])

        # Extract statistics from the merged descriptions.
        wrangler = Wrangler(descriptions, self._category)
        statistics = wrangler.calculate_frequency_distribution()

        if save:
            wrangler.save_statistics(statistics, to_db=False)


if __name__ == "__main__":
    CATEGORY = "Python"
    crawler = CrawlToCSV(CATEGORY)
    crawler.start()
    crawler.extract_statistics()
