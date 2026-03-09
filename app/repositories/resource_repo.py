from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.resource import Resource

class ResourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_resources(self, subject_id: int, rtype: str | None = None) -> list[Resource]:
        q = select(Resource).where(Resource.subject_id == subject_id, Resource.is_active == True)
        if rtype:
            q = q.where(Resource.type == rtype)
        return list(self.db.scalars(q.order_by(Resource.title)))
