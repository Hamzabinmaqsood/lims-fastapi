from pydantic import BaseModel, Field, EmailStr, ConfigDict


class SignupIn(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    mobile_number: str = Field(pattern=r"^03\d{9}$")  # 03XXXXXXXXX
    password: str = Field(min_length=6)
    province_id: int
    district_id: int
    tehsil_id: int
    locality_id: int = Field(..., alias="city_village_id")
    reference_code: str | None = None

    model_config = {
        "populate_by_name": True  # Allows instantiating using locality_id inside Python
    }


class SignupOut(BaseModel):
    message: str
    user_id: int
    username: str
    mobile_number: str


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str | None = Field(None, min_length=1, max_length=150)
    province_id: int | None = None
    district_id: int | None = None
    tehsil_id: int | None = None
    locality_id: int | None = None

class DetailsIn(BaseModel):
    """Validation for the text fields of the details form."""

    cnic: str | None = Field(None, pattern=r"^\d{13}$")
    email: EmailStr | None = None
