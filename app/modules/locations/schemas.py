from pydantic import BaseModel, ConfigDict


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # read from SQLAlchemy objects

    id: int
    name: str
    latitude: float
    longitude: float
