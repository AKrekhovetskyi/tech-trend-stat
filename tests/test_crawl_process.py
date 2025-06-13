from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from database import CollectionVacancies
from techtrendscrape.spiders.djinni import DjinniSpider


def test_crawl_process() -> None:
    process = CrawlerProcess(get_project_settings())
    process.crawl(DjinniSpider)
    process.start()

    with CollectionVacancies() as collection_vacancies:
        assert collection_vacancies.collection.count_documents({})
