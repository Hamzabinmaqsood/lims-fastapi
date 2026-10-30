from pydantic import BaseModel, ConfigDict


class CropSeasonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CropTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    season_id: int
