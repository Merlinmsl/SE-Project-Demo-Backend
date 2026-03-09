from pydantic import BaseModel, Field

class SubjectOut(BaseModel):
    id: int
    grade_id: int
    name: str

class SubjectSelectionIn(BaseModel):
    subject_ids: list[int] = Field(default_factory=list)
