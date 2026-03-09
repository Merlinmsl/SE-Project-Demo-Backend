from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.core.security import AuthUser
from app.repositories.student_repo import StudentRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.subject_repo import SubjectRepository
from app.schemas.resource import ResourceOut
from app.services.storage_service import get_storage_service

router = APIRouter()


@router.get("/resources", response_model=list[ResourceOut])
def list_resources(
    subject_id: int = Query(...),
    type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """List resources (PDFs) for a subject.

    - Requires profile completion (MIN-16).
    - Requires that the subject is selected by the student (MIN-18).
    - Returns a signed view URL for private Supabase Storage (recommended).
    """
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)

    if not st.profile_completed:
        raise HTTPException(status_code=403, detail="Complete profile before accessing resources")

    subj_repo = SubjectRepository(db)
    if not subj_repo.is_subject_selected(st.id, int(subject_id)):
        raise HTTPException(status_code=403, detail="Subject not selected by student")

    repo = ResourceRepository(db)
    resources = repo.list_resources(subject_id=subject_id, rtype=type)

    storage = get_storage_service()
    out: list[ResourceOut] = []
    for r in resources:
        view_url = None
        if r.storage_path:
            try:
                view_url = storage.create_signed_view_url(r.storage_path)
            except Exception as e:
                # If storage isn't configured, return a clear error rather than hiding it.
                raise HTTPException(status_code=500, detail=f"Failed to create signed URL: {e}")
        out.append(
            ResourceOut(
                id=r.id,
                subject_id=r.subject_id,
                type=r.type,
                title=r.title,
                description=r.description,
                view_url=view_url,
                file_url=r.file_url,
                storage_path=r.storage_path,
            )
        )
    return out
