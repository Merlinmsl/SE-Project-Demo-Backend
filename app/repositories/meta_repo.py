from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.province import Province
from app.models.district import District
from app.models.grade import Grade
class MetaRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_provinces(self) -> list[Province]:
        return list(self.db.scalars(select(Province).order_by(Province.name)))

    def list_districts(self, province_id: int | None = None) -> list[District]:
        q = select(District).order_by(District.name)
        if province_id is not None:
            q = q.where(District.province_id == province_id)
        return list(self.db.scalars(q))

    def get_district(self, district_id: int) -> District | None:
        return self.db.scalar(select(District).where(District.id == district_id))

    def get_grade(self, grade_id: int) -> Grade | None:
        return self.db.scalar(select(Grade).where(Grade.id == grade_id))

    def list_grades(self) -> list[Grade]:
        return list(self.db.scalars(select(Grade).where(Grade.is_active == True).order_by(Grade.id)))
