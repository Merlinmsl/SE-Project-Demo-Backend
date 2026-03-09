from pydantic import BaseModel

class ProvinceOut(BaseModel):
    id: int
    name: str

class DistrictOut(BaseModel):
    id: int
    name: str
    province: ProvinceOut

class GradeOut(BaseModel):
    id: int
    name: str

class AvatarCatalogOut(BaseModel):
    avatar_key: str
    label: str
