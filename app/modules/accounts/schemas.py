from pydantic import BaseModel, Field, EmailStr


class SignupIn(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    mobile_number: str = Field(pattern=r"^03\d{9}$")  # 03XXXXXXXXX
    password: str = Field(min_length=6)
    province_id: int
    district_id: int
    tehsil_id: int
    locality_id: int
    reference_code: str | None = None


class SignupOut(BaseModel):
    message: str
    user_id: int
    username: str
    mobile_number: str


class ProfileUpdate(BaseModel):
    username: str | None = Field(None, min_length=1, max_length=150)
    email: EmailStr | None = None
    cnic: str | None = Field(None, pattern=r"^\d{13}$")
    province_id: int | None = None
    district_id: int | None = None
    tehsil_id: int | None = None
    locality_id: int | None = None
