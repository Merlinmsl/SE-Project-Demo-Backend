from pydantic import BaseModel
class StudentCountOut(BaseModel):
    count: int
