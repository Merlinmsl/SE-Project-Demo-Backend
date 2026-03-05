from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.meta_repo import MetaRepository
from app.schemas.meta import ProvinceOut, DistrictOut, GradeOut, AvatarCatalogOut

router = APIRouter()

@router.get("/meta/provinces", response_model=list[ProvinceOut])
def list_provinces(db: Session = Depends(get_db)):
    repo = MetaRepository(db)
    return [ProvinceOut(id=p.id, name=p.name) for p in repo.list_provinces()]

@router.get("/meta/districts", response_model=list[DistrictOut])
def list_districts(province_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    repo = MetaRepository(db)
    out = []
    for d in repo.list_districts(province_id=province_id):
        out.append(DistrictOut(id=d.id, name=d.name, province=ProvinceOut(id=d.province.id, name=d.province.name)))
    return out

@router.get("/meta/grades", response_model=list[GradeOut])
def list_grades(db: Session = Depends(get_db)):
    repo = MetaRepository(db)
    return [GradeOut(id=g.id, name=g.name) for g in repo.list_grades()]

@router.get("/meta/avatars", response_model=list[AvatarCatalogOut])
def list_avatars():
    return [
        {"avatar_key": "avatar_1", "label": "Avatar 1"},
        {"avatar_key": "avatar_2", "label": "Avatar 2"},
        {"avatar_key": "avatar_3", "label": "Avatar 3"},
        {"avatar_key": "avatar_4", "label": "Avatar 4"},
    ]