from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Lat = Annotated[float, Field(ge=-90, le=90)]
Lng = Annotated[float, Field(ge=-180, le=180)]
LatLng = tuple[Lat, Lng]  # JSON: [31.52, 74.35]


class FarmIn(BaseModel):
    name: str = Field("farm", max_length=100)
    boundary: list[LatLng] = Field(min_length=3)  # a shape needs 3+ corners
    crop_season_id: int | None = None
    crop_id: int | None = None
    district_id: int | None = None
    sowing_date: date | None = None


class FarmUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=100)
    boundary: list[LatLng] | None = Field(None, min_length=3)
    crop_season_id: int | None = None
    crop_id: int | None = None
    district_id: int | None = None
    sowing_date: date | None = None


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
