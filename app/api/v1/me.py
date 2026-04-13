from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import AuthUser
from app.db.session import get_db
from app.repositories.student_repo import StudentRepository
from app.repositories.meta_repo import MetaRepository
from app.repositories.subject_repo import SubjectRepository
from app.services.profile_service import ProfileService
from app.schemas.student import StudentProfileOut, StudentProfileUpdateIn, StudentOnboardingIn
from app.schemas.meta import ProvinceOut, GradeOut
from app.schemas.badge import StudentBadgeOut, DistrictRankOut
from app.repositories.badge_repository import badge_repository
from app.services.badge_service import badge_service

router = APIRouter()


def _to_profile_out(student) -> StudentProfileOut:

    district_out = None
    province_out = None
    if student.district:
        province_out = ProvinceOut(id=student.district.province.id, name=student.district.province.name)
        district_out = {
            "id": student.district.id,
            "name": student.district.name,
            "province": province_out,
        }

    grade_out = GradeOut(id=student.grade.id, name=student.grade.name) if student.grade else None

    return StudentProfileOut(
        id=student.id,
        email=student.email,
        full_name=student.full_name,
        username=student.username,
        grade=grade_out,
        district=district_out,
        province=province_out,
        avatar_key=student.avatar_key,
        profile_completed=student.profile_completed,
    )


@router.get("/me/profile", response_model=StudentProfileOut)
def get_my_profile(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    st_repo = StudentRepository(db)
    svc = ProfileService(db)
    st = st_repo.create_if_missing(user)

    is_complete = svc.recompute_profile_completed(st)
    if is_complete != st.profile_completed:
        st = st_repo.update(st, profile_completed=is_complete)

    return _to_profile_out(st)


@router.post("/me/onboarding", response_model=StudentProfileOut)
def complete_onboarding(payload: StudentOnboardingIn, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Completes the mandatory profile completion flow (MIN-13, MIN-16).

    - Validates province -> districts relationship (province-first dropdown UX).
    - Inserts/updates Student row and selected subjects.
    - Sets profile_completed = true only if *all* required fields exist.
    """
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)

    meta = MetaRepository(db)
    district = meta.get_district(payload.district_id)
    if not district:
        raise HTTPException(status_code=400, detail="Invalid district_id")
    if district.province_id != payload.province_id:
        raise HTTPException(status_code=400, detail="district_id does not belong to the selected province_id")
    if not meta.get_grade(payload.grade_id):
        raise HTTPException(status_code=400, detail="Invalid grade_id")

    avatar_key = payload.avatar_key.strip()
    if not avatar_key:
        raise HTTPException(status_code=400, detail="avatar_key cannot be empty")

    new_username = payload.username.strip()
    if len(new_username) < 3:
        raise HTTPException(status_code=400, detail="username must be at least 3 characters")
    existing = st_repo.get_by_username(new_username)
    if existing and existing.id != st.id:
        raise HTTPException(status_code=409, detail="username already taken")

    # Validate subjects allowed for grade
    subj_repo = SubjectRepository(db)
    allowed = subj_repo.list_subjects_for_grade(payload.grade_id)
    allowed_ids = {s.id for s in allowed}
    bad = [sid for sid in payload.subject_ids if sid not in allowed_ids]
    if bad:
        raise HTTPException(status_code=400, detail=f"Subjects not allowed for this grade: {bad}")

    # Update DB profile fields
    st = st_repo.update(
        st,
        full_name=payload.full_name.strip(),
        username=new_username,
        grade_id=payload.grade_id,
        district_id=payload.district_id,
        avatar_key=avatar_key,
        email=st.email or user.email,
    )

    if not st.email:
        raise HTTPException(
            status_code=400,
            detail="Missing email. In dev mode, pass X-Email header; in prod Clerk token includes email.",
        )

    # Save subject selection
    subj_repo.replace_selected_subjects(st.id, payload.subject_ids)

    # Compute completion
    svc = ProfileService(db)
    if not svc.recompute_profile_completed(st):
        raise HTTPException(status_code=400, detail="Profile is still incomplete (missing required fields).")

    st = st_repo.update(st, profile_completed=True)
    return _to_profile_out(st)


@router.put("/me/profile", response_model=StudentProfileOut)
def update_my_profile(payload: StudentProfileUpdateIn, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Edits student profile (MIN-15).

    Note: We keep the profile-completed rule strict:
    - You can't clear required fields once completed.
    - If you change fields, completion is recalculated.
    """
    st_repo = StudentRepository(db)
    meta = MetaRepository(db)
    st = st_repo.create_if_missing(user)

    update_fields = payload.model_dump(exclude_unset=True)
    if not update_fields:
        return _to_profile_out(st)

    # Province/district validation
    if "district_id" in update_fields and update_fields["district_id"] is not None:
        district = meta.get_district(int(update_fields["district_id"]))
        if not district:
            raise HTTPException(status_code=400, detail="Invalid district_id")
        if update_fields.get("province_id") is not None and district.province_id != int(update_fields["province_id"]):
            raise HTTPException(status_code=400, detail="district_id does not belong to the selected province_id")

    if "grade_id" in update_fields and update_fields["grade_id"] is not None:
        if not meta.get_grade(int(update_fields["grade_id"])):
            raise HTTPException(status_code=400, detail="Invalid grade_id")

    if "avatar_key" in update_fields and update_fields["avatar_key"] is not None:
        avatar_key = str(update_fields["avatar_key"]).strip()
        if not avatar_key:
            raise HTTPException(status_code=400, detail="avatar_key cannot be empty")
        update_fields["avatar_key"] = avatar_key

    if "username" in update_fields and update_fields["username"] is not None:
        new_username = update_fields["username"].strip()
        if len(new_username) < 3:
            raise HTTPException(status_code=400, detail="username must be at least 3 characters")
        existing = st_repo.get_by_username(new_username)
        if existing and existing.id != st.id:
            raise HTTPException(status_code=409, detail="username already taken")
        update_fields["username"] = new_username

    if "full_name" in update_fields and update_fields["full_name"] is not None:
        update_fields["full_name"] = update_fields["full_name"].strip()

    # If profile already completed, required fields cannot be cleared.
    if st.profile_completed:
        for key in ("full_name", "username", "grade_id", "district_id", "avatar_key"):
            if key in update_fields and update_fields[key] is None:
                raise HTTPException(status_code=400, detail=f"{key} cannot be cleared once profile is completed")

    # province_id is not stored (derived from district)
    update_fields.pop("province_id", None)

    st = st_repo.update(st, **update_fields)

    # Recompute completion status
    svc = ProfileService(db)
    is_complete = svc.recompute_profile_completed(st)
    if is_complete != st.profile_completed:
        st = st_repo.update(st, profile_completed=is_complete)

    return _to_profile_out(st)


@router.get("/me/badges", response_model=list[StudentBadgeOut])
def get_my_badges(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Retrieve all badges earned by the authenticated student."""
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)
    
    records = badge_repository.get_badges_for_student(st.id, db)
    
    results = []
    for sb, b in records:
        results.append(StudentBadgeOut(
            id=sb.id,
            student_id=sb.student_id,
            awarded_at=sb.awarded_at,
            badge={
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "image_url": b.image_url,
                "category": b.category,
            }
def _to_profile_out(student) -> StudentProfileOut:

    district_out = None
    province_out = None
    if student.district:
        province_out = ProvinceOut(id=student.district.province.id, name=student.district.province.name)
        district_out = {
            "id": student.district.id,
            "name": student.district.name,
            "province": province_out,
        }

    grade_out = GradeOut(id=student.grade.id, name=student.grade.name) if student.grade else None

    return StudentProfileOut(
        id=student.id,
        email=student.email,
        full_name=student.full_name,
        username=student.username,
        grade=grade_out,
        district=district_out,
        province=province_out,
        avatar_key=student.avatar_key,
        profile_completed=student.profile_completed,
    )


@router.get("/me/profile", response_model=StudentProfileOut)
def get_my_profile(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    st_repo = StudentRepository(db)
    svc = ProfileService(db)
    st = st_repo.create_if_missing(user)

    is_complete = svc.recompute_profile_completed(st)
    if is_complete != st.profile_completed:
        st = st_repo.update(st, profile_completed=is_complete)

    return _to_profile_out(st)


@router.post("/me/onboarding", response_model=StudentProfileOut)
def complete_onboarding(payload: StudentOnboardingIn, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Completes the mandatory profile completion flow (MIN-13, MIN-16).

    - Validates province -> districts relationship (province-first dropdown UX).
    - Inserts/updates Student row and selected subjects.
    - Sets profile_completed = true only if *all* required fields exist.
    """
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)

    meta = MetaRepository(db)
    district = meta.get_district(payload.district_id)
    if not district:
        raise HTTPException(status_code=400, detail="Invalid district_id")
    if district.province_id != payload.province_id:
        raise HTTPException(status_code=400, detail="district_id does not belong to the selected province_id")
    if not meta.get_grade(payload.grade_id):
        raise HTTPException(status_code=400, detail="Invalid grade_id")

    avatar_key = payload.avatar_key.strip()
    if not avatar_key:
        raise HTTPException(status_code=400, detail="avatar_key cannot be empty")

    new_username = payload.username.strip()
    if len(new_username) < 3:
        raise HTTPException(status_code=400, detail="username must be at least 3 characters")
    existing = st_repo.get_by_username(new_username)
    if existing and existing.id != st.id:
        raise HTTPException(status_code=409, detail="username already taken")

    # Validate subjects allowed for grade
    subj_repo = SubjectRepository(db)
    allowed = subj_repo.list_subjects_for_grade(payload.grade_id)
    allowed_ids = {s.id for s in allowed}
    bad = [sid for sid in payload.subject_ids if sid not in allowed_ids]
    if bad:
        raise HTTPException(status_code=400, detail=f"Subjects not allowed for this grade: {bad}")

    # Update DB profile fields
    st = st_repo.update(
        st,
        full_name=payload.full_name.strip(),
        username=new_username,
        grade_id=payload.grade_id,
        district_id=payload.district_id,
        avatar_key=avatar_key,
        email=st.email or user.email,
    )

    if not st.email:
        raise HTTPException(
            status_code=400,
            detail="Missing email. In dev mode, pass X-Email header; in prod Clerk token includes email.",
        )

    # Save subject selection
    subj_repo.replace_selected_subjects(st.id, payload.subject_ids)

    # Compute completion
    svc = ProfileService(db)
    if not svc.recompute_profile_completed(st):
        raise HTTPException(status_code=400, detail="Profile is still incomplete (missing required fields).")

    st = st_repo.update(st, profile_completed=True)
    return _to_profile_out(st)


@router.put("/me/profile", response_model=StudentProfileOut)
def update_my_profile(payload: StudentProfileUpdateIn, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Edits student profile (MIN-15).

    Note: We keep the profile-completed rule strict:
    - You can't clear required fields once completed.
    - If you change fields, completion is recalculated.
    """
    st_repo = StudentRepository(db)
    meta = MetaRepository(db)
    st = st_repo.create_if_missing(user)

    update_fields = payload.model_dump(exclude_unset=True)
    if not update_fields:
        return _to_profile_out(st)

    # Province/district validation
    if "district_id" in update_fields and update_fields["district_id"] is not None:
        district = meta.get_district(int(update_fields["district_id"]))
        if not district:
            raise HTTPException(status_code=400, detail="Invalid district_id")
        if update_fields.get("province_id") is not None and district.province_id != int(update_fields["province_id"]):
            raise HTTPException(status_code=400, detail="district_id does not belong to the selected province_id")

    if "grade_id" in update_fields and update_fields["grade_id"] is not None:
        if not meta.get_grade(int(update_fields["grade_id"])):
            raise HTTPException(status_code=400, detail="Invalid grade_id")

    if "avatar_key" in update_fields and update_fields["avatar_key"] is not None:
        avatar_key = str(update_fields["avatar_key"]).strip()
        if not avatar_key:
            raise HTTPException(status_code=400, detail="avatar_key cannot be empty")
        update_fields["avatar_key"] = avatar_key

    if "username" in update_fields and update_fields["username"] is not None:
        new_username = update_fields["username"].strip()
        if len(new_username) < 3:
            raise HTTPException(status_code=400, detail="username must be at least 3 characters")
        existing = st_repo.get_by_username(new_username)
        if existing and existing.id != st.id:
            raise HTTPException(status_code=409, detail="username already taken")
        update_fields["username"] = new_username

    if "full_name" in update_fields and update_fields["full_name"] is not None:
        update_fields["full_name"] = update_fields["full_name"].strip()

    # If profile already completed, required fields cannot be cleared.
    if st.profile_completed:
        for key in ("full_name", "username", "grade_id", "district_id", "avatar_key"):
            if key in update_fields and update_fields[key] is None:
                raise HTTPException(status_code=400, detail=f"{key} cannot be cleared once profile is completed")

    # province_id is not stored (derived from district)
    update_fields.pop("province_id", None)

    st = st_repo.update(st, **update_fields)

    # Recompute completion status
    svc = ProfileService(db)
    is_complete = svc.recompute_profile_completed(st)
    if is_complete != st.profile_completed:
        st = st_repo.update(st, profile_completed=is_complete)

    return _to_profile_out(st)


@router.get("/me/badges", response_model=list[StudentBadgeOut])
def get_my_badges(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Retrieve all badges earned by the authenticated student."""
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)
    
    records = badge_repository.get_badges_for_student(st.id, db)
    
    results = []
    for sb, b in records:
        results.append(StudentBadgeOut(
            id=sb.id,
            student_id=sb.student_id,
            awarded_at=sb.awarded_at,
            badge={
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "image_url": b.image_url,
                "category": b.category,
            }
        ))
        
    return results


@router.get("/me/district-rank", response_model=DistrictRankOut)
def get_my_district_rank(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    """Retrieve the student's current district ranking and update Top 10 badges."""
    st_repo = StudentRepository(db)
    st = st_repo.create_if_missing(user)
    
    # This evaluates their current rank based on total XP and automatically 
    # awards any eligible Top 10 badges.
    # We call it here so when the frontend asks for the rank, it is freshly computed.
    rank = badge_service.evaluate_district_ranking(db, st.id)
    
    district_name = st.district.name if st.district else None
    
    # Has a badge?
    # We get all their badges and see if there's a district badge
    student_badges = badge_repository.get_badges_for_student(st.id, db)
    district_badge = next((b for sb, b in student_badges if b.category == "district"), None)
    
    return DistrictRankOut(
        rank=rank,
        district_id=st.district_id,
        district_name=district_name,
        has_badge=district_badge is not None,
        badge_name=district_badge.name if district_badge else None
    )
