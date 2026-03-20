from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import require_admin_api_key
from app.repositories.resource_repo import ResourceRepository
from app.schemas.resource import ResourceCreateIn, ResourceUpdateIn, ResourceOut
from typing import Optional

router = APIRouter(prefix="/admin/resources", tags=["admin-resources"])


@router.post("", response_model=ResourceOut, dependencies=[Depends(require_admin_api_key)])
def create_resource(data: ResourceCreateIn, db: Session = Depends(get_db)):
    """Add a new resource to the platform (admin only)."""
    repo = ResourceRepository(db)
    resource = repo.create(data.model_dump())
    return ResourceOut(
        id=resource.id,
        subject_id=resource.subject_id,
        type=resource.type,
        title=resource.title,
        description=resource.description,
        is_active=resource.is_active,
        file_url=resource.file_url,
        storage_path=resource.storage_path,
    )


@router.put("/{resource_id}", response_model=ResourceOut, dependencies=[Depends(require_admin_api_key)])
def update_resource(resource_id: int, data: ResourceUpdateIn, db: Session = Depends(get_db)):
    """Update an existing resource (admin only)."""
    repo = ResourceRepository(db)
    resource = repo.get_by_id(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    resource = repo.update(resource, updates)
    return ResourceOut(
        id=resource.id,
        subject_id=resource.subject_id,
        type=resource.type,
        title=resource.title,
        description=resource.description,
        is_active=resource.is_active,
        file_url=resource.file_url,
        storage_path=resource.storage_path,
    )


@router.delete("/{resource_id}", dependencies=[Depends(require_admin_api_key)])
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    """Soft-delete a resource so students no longer see it (admin only)."""
    repo = ResourceRepository(db)
    resource = repo.get_by_id(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    repo.soft_delete(resource)
    return {"detail": "Resource removed"}


@router.patch("/{resource_id}/toggle", response_model=ResourceOut, dependencies=[Depends(require_admin_api_key)])
def toggle_resource(resource_id: int, db: Session = Depends(get_db)):
    """Toggle a resource between active and inactive (admin only)."""
    repo = ResourceRepository(db)
    resource = repo.get_by_id(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    resource = repo.toggle_active(resource)
    return ResourceOut(
        id=resource.id,
        subject_id=resource.subject_id,
        type=resource.type,
        title=resource.title,
        description=resource.description,
        is_active=resource.is_active,
        file_url=resource.file_url,
        storage_path=resource.storage_path,
    )


@router.get("", response_model=list[ResourceOut], dependencies=[Depends(require_admin_api_key)])
def list_all_resources(subject_id: Optional[int] = Query(default=None), db: Session = Depends(get_db)):
    """List all resources including inactive ones (admin only)."""
    repo = ResourceRepository(db)
    resources = repo.list_all_resources(subject_id=subject_id)
    return [
        ResourceOut(
            id=r.id,
            subject_id=r.subject_id,
            type=r.type,
            title=r.title,
            description=r.description,
            is_active=r.is_active,
            file_url=r.file_url,
            storage_path=r.storage_path,
        )
        for r in resources
    ]
