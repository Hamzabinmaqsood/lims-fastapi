from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator,StringConstraints

StageName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

IndexName = Literal["NDVI", "SAVI", "MSAVI", "NDMI", "NDRE", "RECI"]
IndexValue = Field(ge=-1, le=1, max_digits=4, decimal_places=3)


class RangeIn(BaseModel):
    index_name: IndexName
    low: Decimal = IndexValue
    high: Decimal = IndexValue
    title: str | None = Field(None, max_length=255)
    description: str | None = None

    @model_validator(mode="after")
    def low_not_above_high(self):
        if self.low > self.high:
            raise ValueError("low must not be greater than high")
        return self


class StageIn(BaseModel):
    crop_id: int
    name: StageName
    day_from: int = Field(ge=0, le=366)
    day_to: int = Field(ge=0, le=366)
    ranges: list[RangeIn] = []

    @model_validator(mode="after")
    def check(self):
        if self.day_to < self.day_from:
            raise ValueError("day_to must not be before day_from")
        names = [r.index_name for r in self.ranges]
        if len(names) != len(set(names)):
            raise ValueError("Each index can appear only once per stage")
        return self


class RangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index_name: str
    low: float
    high: float
    title: str | None
    description: str | None


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crop_id: int
    name: str
    day_from: int
    day_to: int
    ranges: list[RangeOut]

