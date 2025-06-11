from collections.abc import Generator, Iterable
from datetime import datetime
from typing import Any, ClassVar
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import scrapy
from parsel.selector import Selector
from scrapy.http import Request, Response

from database import VacancyItem


class NotFoundError(Exception): ...


class DjinniSpider(scrapy.Spider):
    """Pass any number of categories as a string separated by a `" | "`.
    For example `"C# / .NET | Python"`. The category name can be
    found on the Djinni website.
    """

    name = "djinni"
    allowed_domains: ClassVar[list[str]] = ["djinni.co"]  # type: ignore[reportIncompatibleVariableOverride]
    start_urls: ClassVar[list[str]] = ["https://djinni.co/jobs/"]  # type: ignore[reportIncompatibleVariableOverride]
    categories = "Python"
    category: str

    def start_requests(self) -> Iterable[Request]:
        for url in self.start_urls:
            for primary_keyword in self.categories.split(" | "):
                self.category = primary_keyword
                yield Request(
                    f"{url}?primary_keyword={quote_plus(primary_keyword)}",
                    dont_filter=True,
                )

    @staticmethod
    def css_get(selector: Selector, query: str) -> str:
        if not (selector_list := selector.css(query)):
            raise NotFoundError(query)
        return selector_list[0].get()

    def _parse_job_item(self, selector: Selector) -> VacancyItem:
        years_of_experience, company_type = 0, None
        for job_info in selector.css(".job-list-item__job-info span::text"):
            if experience := job_info.re(r"\b(\d+)\b"):
                years_of_experience = int(experience[0])
            if "Product" in job_info.get():
                company_type = "Product"
        statistics = selector.css("span.text-muted span.nobr .mr-2::attr(title)")
        publication_date = self.css_get(selector, "span.text-muted span.mr-2.nobr::attr(title)")
        return VacancyItem(
            source=self.name,
            category=self.category,
            company_name=self.css_get(selector, "header a.mr-2::text").strip(),
            company_type=company_type or "Outsource/staff",
            description=self.css_get(selector, ".job-list-item__description span::attr(data-original-text)"),
            years_of_experience=years_of_experience,
            publication_date=datetime.strptime(publication_date, "%H:%M %d.%m.%Y").replace(
                tzinfo=ZoneInfo("Europe/Kyiv")
            ),
            views=int(statistics[0].get().split()[0]),
            applications=int(statistics[1].get().split()[0]),
        )

    def parse(self, response: Response) -> Generator[Request | VacancyItem, Any]:
        for job_item in response.css("ul .list-jobs__item"):
            yield self._parse_job_item(job_item)
        if (next_page := response.css(".pagination li.active + li a")) and (link := next_page[0].attrib.get("href")):
            yield response.follow(link, callback=self.parse)
