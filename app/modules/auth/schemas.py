from pydantic import BaseModel


class LoginIn(BaseModel):
    mobile_number: str
    password: str


class LoginOut(BaseModel):
    refresh: str
    access: str
    user_id: int
    user_role: str
    user_name: str
