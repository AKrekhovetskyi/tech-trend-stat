from collections.abc import Generator, Iterable
from datetime import datetime
from typing import Any, ClassVar
from urllib.parse import quote_plus, unquote_plus
from zoneinfo import ZoneInfo

import scrapy
from scrapy.http import Request, Response

from database import VacancyItem


class DjinniSpider(scrapy.Spider):
    """Pass any number of categories as a string separated by a `" | "`.
    For example `"C# / .NET | Python"`. The category name can be
    found on the Djinni website.
    """

    name = "djinni"
    allowed_domains: ClassVar[list[str]] = ["djinni.co"]
    start_urls: ClassVar[list[str]] = ["https://djinni.co/jobs/"]
    categories = "Python"

    def start_requests(self) -> Iterable[Request]:
        for url in self.start_urls:
            for primary_keyword in self.categories.split(" | "):
                yield Request(
                    f"{url}?primary_keyword={quote_plus(primary_keyword)}",
                    dont_filter=True,
                )

    def _parse_job_item(self, selector: scrapy.Selector, category: str) -> VacancyItem:
        years_of_experience, company_type = 0, None
        for job_info in selector.css(".job-list-item__job-info span::text"):
            if experience := job_info.re(r"\b(\d+)\b"):
                years_of_experience = int(experience[0])
            if "Product" in job_info.get():
                company_type = "Product"
        statistics = selector.css("span.text-muted span.nobr .mr-2::attr(title)")
        return VacancyItem(
            source=self.name,
            category=category,
            company_name=selector.css("header a.mr-2::text").get().strip(),
            company_type=company_type or "Outsource/staff",
            description=selector.css(".job-list-item__description span::attr(data-original-text)").get(),
            years_of_experience=years_of_experience,
            publication_date=datetime.strptime(
                selector.css("span.text-muted span.mr-2.nobr::attr(title)").get(), "%H:%M %d.%m.%Y"
            ).replace(tzinfo=ZoneInfo("Europe/Kyiv")),
            views=int(statistics[0].get().split()[0]),
            applications=int(statistics[1].get().split()[0]),
        )

    def parse(self, response: Response) -> Generator[VacancyItem, Any]:
        category = unquote_plus(response.request.url.split("=")[1].split("&")[0])
        for job_item in response.css("ul .list-jobs__item"):
            yield self._parse_job_item(job_item, category)
        if next_page := response.css(".pagination li.active + li a"):
            yield response.follow(next_page[0], callback=self.parse)
