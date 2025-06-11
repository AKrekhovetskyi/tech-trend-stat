# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

import csv
from pathlib import Path

from database import DatabaseVacancies, VacancyItem
from techtrendscrape.spiders.djinni import DjinniSpider


class MongoPipeline(DatabaseVacancies):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[VacancyItem] = []

    def close_spider(self, spider: DjinniSpider) -> None:
        collection = self.connect_collection()
        collection.bulk_write(self.create_replacements(self.items))
        self.client.close()

    def process_item(self, item: VacancyItem, spider: DjinniSpider) -> VacancyItem:
        self.items.append(item)
        return item


class CSVPipeline(MongoPipeline):
    def close_spider(self, spider: DjinniSpider) -> None:
        fieldnames = VacancyItem.model_fields.keys()
        with Path(f"{self.collection}.csv").open("w") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([item.model_dump() for item in self.items])
