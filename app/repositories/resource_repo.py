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

    def get_by_id(self, resource_id: int) -> Resource | None:
        return self.db.get(Resource, resource_id)

    def create(self, data: dict) -> Resource:
        resource = Resource(**data)
        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def update(self, resource: Resource, updates: dict) -> Resource:
        for key, value in updates.items():
            setattr(resource, key, value)
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def soft_delete(self, resource: Resource) -> None:
        resource.is_active = False
        self.db.commit()

    def toggle_active(self, resource: Resource) -> Resource:
        resource.is_active = not resource.is_active
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def list_all_resources(self, subject_id: int | None = None) -> list[Resource]:
        """List all resources including inactive ones (for admin use)."""
        q = select(Resource)
        if subject_id:
            q = q.where(Resource.subject_id == subject_id)
        return list(self.db.scalars(q.order_by(Resource.title)))
