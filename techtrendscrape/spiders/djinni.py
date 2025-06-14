import json
import logging
from collections.abc import AsyncIterator, Generator
from datetime import datetime
from secrets import choice
from typing import Any, ClassVar
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import scrapy
from fake_useragent import UserAgent
from parsel.selector import Selector, SelectorList
from scrapy.http import Request, Response

from database import InteractionStats, VacancyItem

ua = UserAgent()
default_request_headers = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,en-US,en;q=0.8,ru;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "djinni.co",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
}


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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.category: str
        self.job_offers: dict[int, dict[str, Any]] = {}
        super().__init__(*args, **kwargs)

    async def start(self) -> AsyncIterator[Request]:
        for url in self.start_urls:
            for primary_keyword in self.categories.split(" | "):
                self.category = primary_keyword
                yield Request(
                    f"{url}?primary_keyword={quote_plus(primary_keyword)}",
                    headers={
                        "Referer": f"https://djinni.co/jobs/?primary_keyword={quote_plus(primary_keyword)}",
                        "User-Agent": ua.random,
                    }
                    | default_request_headers,
                    meta={"proxy": f"http://{choice(self.settings['PROXY_LIST'])}"}
                    if self.settings["PROXY_LIST"]
                    else None,
                )

    def _extract_job_offers(self, selector: SelectorList) -> None:
        json_text = selector.xpath('//script[@type="application/ld+json"]/text()').get()

        if not json_text:
            raise ValueError(f"{json_text=}")
        for offer in json.loads(json_text):
            application_location = offer.get("applicantLocationRequirements")
            if isinstance(application_location, list):
                address = offer["applicantLocationRequirements"][0]["address"]
            elif isinstance(application_location, dict):
                address = offer["applicantLocationRequirements"]["address"]
            else:
                address = {}

            try:
                self.job_offers[offer["identifier"]] = {
                    "address": address.get("addressCountry")
                    or address.get("addressLocality")
                    or address.get("addressRegion")
                    or address.get("postalCode"),
                    "publication_date": offer["datePosted"],
                    "description": offer["description"],
                    "years_of_experience": round(
                        offer.get("experienceRequirements", {"monthsOfExperience": 0})["monthsOfExperience"] / 12, 2
                    ),
                    "company_name": None
                    if isinstance(offer["hiringOrganization"], str)
                    else offer["hiringOrganization"]["name"],
                    "title": offer["title"],
                    "url": offer["url"],
                }
            except (KeyError, TypeError):
                self.log(f"{offer=}", level=logging.ERROR)
                raise

    def _parse_interaction_stats(self, selector: Selector) -> InteractionStats:
        views_text = selector.css("span.text-nowrap:contains('перегляд')::text").re_first(r"(\d+)")
        if not views_text:
            raise ValueError(f"{views_text=}, {selector=!s}")

        applications_text = selector.css("span.text-nowrap:contains('відгук')::text").re_first(r"(\d+)")
        if not applications_text:
            raise ValueError(f"{applications_text=}, {selector=!s}")

        return InteractionStats(views=int(views_text), applications=int(applications_text))

    def parse(self, response: Response) -> Generator[Request | VacancyItem, Any]:
        self._extract_job_offers(response.css("head"))
        for job_item in response.css("ul.list-jobs li[id*='job-item']"):
            interaction_stats = self._parse_interaction_stats(job_item)
            identifier = int(job_item.attrib["id"].split("-")[-1])
            offer = self.job_offers[identifier]
            yield VacancyItem(
                source=self.name,
                category=self.category,
                company_name=offer["company_name"],
                address=offer["address"],
                title=offer["title"],
                description=offer["description"],
                years_of_experience=offer["years_of_experience"],
                publication_date=datetime.fromisoformat(offer["publication_date"]).replace(
                    tzinfo=ZoneInfo("Europe/Kyiv")
                ),
                url=offer["url"],
                views=interaction_stats.views,
                applications=interaction_stats.applications,
            )
        pagination = response.css("ul.pagination li.page-item")
        if pagination:
            last_li = pagination[-1]
            link = last_li.css("a::attr(href)").get()
            if link:
                yield response.follow(link, callback=self.parse)
        else:
            self.log(f"No more pages found. URL of the last page: {response.url}", level=logging.INFO)
