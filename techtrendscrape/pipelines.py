# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from database import CollectionVacancies, VacancyItem
from techtrendscrape.spiders.djinni import DjinniSpider

if TYPE_CHECKING:
    from pydantic import BaseModel


class Pipeline:
    def __init__(self) -> None:
        self.items: list[BaseModel] = []

    def process_item(self, item: VacancyItem, _: DjinniSpider) -> VacancyItem:
        self.items.append(item)
        return item


class MongoPipeline(Pipeline):
    def close_spider(self, _: DjinniSpider) -> None:
        with CollectionVacancies() as vacancies:
            vacancies.bulk_upsert(("url",), items=self.items)


class CSVPipeline(Pipeline):
    def close_spider(self, _: DjinniSpider) -> None:
        fieldnames = VacancyItem.model_fields.keys()
        with Path(f"{CollectionVacancies.collection_name}.csv").open("w") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([item.model_dump() for item in self.items])
