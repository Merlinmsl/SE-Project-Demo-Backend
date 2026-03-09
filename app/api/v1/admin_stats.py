from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import require_admin_api_key
from app.repositories.admin_repo import AdminRepository
from app.schemas.admin import StudentCountOut

router = APIRouter()

@router.get("/admin/stats/student-count", response_model=StudentCountOut, dependencies=[Depends(require_admin_api_key)])
def get_student_count(db: Session = Depends(get_db)):
    repo = AdminRepository(db)
    return StudentCountOut(count=repo.count_students())
