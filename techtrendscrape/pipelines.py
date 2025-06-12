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


class MongoPipeline(CollectionVacancies):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[BaseModel] = []

    def close_spider(self, _: DjinniSpider) -> None:
        collection = self.connect_collection()
        collection.bulk_write(self.create_replacements(self.items))
        self.client.close()

    def process_item(self, item: VacancyItem, _: DjinniSpider) -> VacancyItem:
        self.items.append(item)
        return item


class CSVPipeline(MongoPipeline):
    def close_spider(self, _: DjinniSpider) -> None:
        fieldnames = VacancyItem.model_fields.keys()
        with Path(f"{self.collection}.csv").open("w") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([item.model_dump() for item in self.items])
