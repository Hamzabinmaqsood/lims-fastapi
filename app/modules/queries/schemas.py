from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QueryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str | None
    image_url: str | None
    voice_url: str | None
    video_url: str | None
    is_done: bool                 # read from the @property
    created_at: datetime
    answered_at: datetime | None


class QueryPage(BaseModel):
    count: int        # total matching queries (for "page 2 of 7")
    page: int
    page_size: int
    results: list[QueryOut]
