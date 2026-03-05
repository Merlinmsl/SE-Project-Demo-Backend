from pydantic import BaseModel, Field
from app.schemas.meta import DistrictOut, ProvinceOut, GradeOut


class StudentProfileOut(BaseModel):
    id: int
    email: str | None = None
    full_name: str | None = None
    username: str | None = None
    grade: GradeOut | None = None
    district: DistrictOut | None = None
    province: ProvinceOut | None = None
    avatar_key: str | None = None
    profile_completed: bool


class StudentProfileUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=150)
    username: str | None = Field(default=None, max_length=50)
    grade_id: int | None = None
    province_id: int | None = None
    district_id: int | None = None
    avatar_key: str | None = Field(default=None, max_length=30)


class StudentOnboardingIn(BaseModel):
    full_name: str = Field(..., max_length=150)
    username: str = Field(..., max_length=50)
    grade_id: int
    province_id: int
    district_id: int
    avatar_key: str = Field(..., max_length=30)
    subject_ids: list[int] = Field(..., min_length=1)
