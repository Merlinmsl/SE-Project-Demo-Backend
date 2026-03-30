from fastapi import APIRouter
from app.api.v1.admin_auth import router as admin_auth_router
from app.api.v1.admin_question import router as admin_question_router
from app.api.v1.admin_resources import router as admin_resources_router
from app.api.v1.student_quiz import router as student_quiz_router
from app.api.v1.me import router as me_router
from app.api.v1.meta import router as meta_router
from app.api.v1.resources import router as resources_router
from app.api.v1.subjects import router as subjects_router
from app.api.v1.admin_stats import router as admin_stats_router
from app.api.v1.admin_resources import router as admin_resources_router
from app.api.v1.student_stats import router as student_stats_router
from app.api.v1.chat import router as chat_router
from app.api.v1.admin_chat import router as admin_chat_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(admin_auth_router)
v1_router.include_router(admin_question_router)
v1_router.include_router(admin_resources_router)
v1_router.include_router(student_quiz_router)
v1_router.include_router(meta_router, tags=["meta"])
v1_router.include_router(me_router, tags=["me"])
v1_router.include_router(subjects_router, tags=["subjects"])
v1_router.include_router(resources_router, tags=["resources"])
v1_router.include_router(admin_stats_router, tags=["admin-stats"])
v1_router.include_router(admin_resources_router)
v1_router.include_router(student_stats_router)
v1_router.include_router(chat_router)
v1_router.include_router(admin_chat_router, tags=["admin-chat"])
