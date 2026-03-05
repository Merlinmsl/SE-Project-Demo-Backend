from fastapi import APIRouter
from app.api.v1.admin_auth import router as admin_auth_router
from app.api.v1.admin_question import router as admin_question_router
from app.api.v1.student_quiz import router as student_quiz_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(admin_auth_router)
v1_router.include_router(admin_question_router)
v1_router.include_router(student_quiz_router)
