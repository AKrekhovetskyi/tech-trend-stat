from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, NonNegativeFloat, NonNegativeInt


class InteractionStats(BaseModel):
    views: NonNegativeInt
    applications: NonNegativeInt


class VacancyItem(InteractionStats):
    source: str = Field(min_length=1)
    category: str = Field(min_length=1)
    company_name: str | None = Field(min_length=1)
    # addressCountry | addressLocality | addressRegion | postalCode.
    address: str | None = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str
    years_of_experience: NonNegativeFloat
    publication_date: datetime
    url: HttpUrl


class Statistics(BaseModel):
    category: str = Field(min_length=1)
    from_datetime: datetime
    to_datetime: datetime
    technology_frequency: dict[str, int]
