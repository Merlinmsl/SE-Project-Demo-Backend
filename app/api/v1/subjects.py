from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.core.security import AuthUser
from app.repositories.subject_repo import SubjectRepository
from app.repositories.student_repo import StudentRepository
from app.services.profile_service import ProfileService
from app.schemas.subject import SubjectOut, SubjectSelectionIn

router = APIRouter()


@router.get("/subjects/available", response_model=list[SubjectOut])
def list_available_subjects(
    grade_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Subjects available for a grade (used in onboarding / subject selection)."""
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)

    gid = grade_id or st.grade_id
    if not gid:
        raise HTTPException(status_code=400, detail="grade_id is required (either set in profile or pass grade_id query)")

    repo = SubjectRepository(db)
    subjects = repo.list_subjects_for_grade(int(gid))
    return [SubjectOut(id=s.id, grade_id=s.grade_id, name=s.name) for s in subjects]


@router.get("/me/subjects", response_model=list[SubjectOut])
def get_my_subjects(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)

    repo = SubjectRepository(db)
    selected = repo.list_selected_subjects(st.id)
    return [SubjectOut(id=ss.subject.id, grade_id=ss.subject.grade_id, name=ss.subject.name) for ss in selected]


@router.put("/me/subjects", response_model=dict)
def set_my_subjects(payload: SubjectSelectionIn, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Set student subject selection (MIN-18).

    Completion status is recalculated after updating subjects.
    """
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)

    if not st.grade_id:
        raise HTTPException(status_code=400, detail="Set grade first before selecting subjects")
    if not payload.subject_ids:
        raise HTTPException(status_code=400, detail="Select at least one subject")

    repo = SubjectRepository(db)
    allowed = repo.list_subjects_for_grade(int(st.grade_id))
    allowed_ids = {s.id for s in allowed}
    bad = [sid for sid in payload.subject_ids if sid not in allowed_ids]
    if bad:
        raise HTTPException(status_code=400, detail=f"Subjects not allowed for this grade: {bad}")

    repo.replace_selected_subjects(st.id, payload.subject_ids)

    svc = ProfileService(db)
    is_complete = svc.recompute_profile_completed(st)
    if is_complete != st.profile_completed:
        st = st_repo.update(st, profile_completed=is_complete)

    return {"ok": True, "selected_count": len(payload.subject_ids), "profile_completed": st.profile_completed}
