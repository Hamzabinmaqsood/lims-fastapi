from datetime import datetime

from pydantic import BaseModel, ConfigDict

class ResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str | None
    image_url: str | None
    voice_url: str | None
    video_url: str | None
    responder_id: int | None
    created_at: datetime


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
    assigned_to_id: int | None
    response: ResponseOut | None


class QueryPage(BaseModel):
    count: int        # total matching queries (for "page 2 of 7")
    page: int
    page_size: int
    results: list[QueryOut]


