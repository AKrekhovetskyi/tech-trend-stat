from datetime import datetime

from pydantic import BaseModel, Field, NonNegativeInt


class VacancyItem(BaseModel):
    source: str = "djinni"
    category: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    company_type: str | None = Field(min_length=1)
    description: str
    years_of_experience: NonNegativeInt
    publication_date: datetime
    views: NonNegativeInt | None
    applications: NonNegativeInt | None


class Statistics(BaseModel):
    category: str = Field(min_length=1)
    from_datetime: datetime
    to_datetime: datetime
    technology_frequency: dict[str, int]
