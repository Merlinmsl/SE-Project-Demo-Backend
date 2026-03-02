from fastapi import APIRouter
from app.api.v1.admin_question import router as admin_question_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(admin_question_router)
