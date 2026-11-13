from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.time import today_pk

Lat = Annotated[float, Field(ge=-90, le=90)]
Lng = Annotated[float, Field(ge=-180, le=180)]
LatLng = tuple[Lat, Lng]  # JSON: [31.52, 74.35]
FarmName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class FarmIn(BaseModel):
    name: FarmName
    boundary: list[LatLng] = Field(min_length=3)  # a shape needs 3+ corners
    crop_season_id: int | None = None
    crop_id: int | None = None
    district_id: int | None = None
    sowing_date: date | None = None

    @field_validator("sowing_date")
    @classmethod
    def not_in_future(cls, value):
        if value is not None and value > today_pk():
            raise ValueError("Sowing date cannot be in the future.")
        return value


class FarmUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: FarmName | None = None
    boundary: list[LatLng] | None = Field(None, min_length=3)
    crop_season_id: int | None = None
    crop_id: int | None = None
    district_id: int | None = None
    sowing_date: date | None = None

    @field_validator("sowing_date")
    @classmethod
    def not_in_future(cls, value):
        if value is not None and value > today_pk():
            raise ValueError("Sowing date cannot be in the future.")
        return value


class FarmOut(BaseModel):
    id: int
    name: str
    boundary: list[list[float]]
    area_acres: float
    crop_season_id: int | None
    crop_id: int | None
    district_id: int | None
    sowing_date: date | None
    created_at: datetime
