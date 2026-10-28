from pydantic import BaseModel, Field


class SignupIn(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    mobile_number: str = Field(pattern=r"^03\d{9}$")  # 03XXXXXXXXX
    password: str = Field(min_length=6)


class SignupOut(BaseModel):
    message: str
    user_id: int
    username: str
    mobile_number: str
