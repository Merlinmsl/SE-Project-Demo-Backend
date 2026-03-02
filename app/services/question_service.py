from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.question import Question
from app.models.admin import Admin
from app.models.subject import Subject
from app.models.topic import Topic
from app.schemas.question import QuestionCreate, QuestionFilter, XP_DEFAULTS
from app.repositories.question_repository import QuestionRepository, question_repository


class QuestionService:
    """Business logic layer for question management."""

    def __init__(self, repository: QuestionRepository):
        self._repo = repository

    def create_question(self, db: Session, data: QuestionCreate) -> Question:
        """Validate inputs, apply XP defaults, and persist a question."""
        # Validate foreign keys exist
        self._validate_admin_exists(db, data.created_by)
        self._validate_subject_exists(db, data.subject_id)
        self._validate_topic_exists(db, data.topic_id)

        # Auto-assign XP if not provided
        xp_value = data.xp_value if data.xp_value is not None else XP_DEFAULTS[data.difficulty]

        # Build the model
        question = Question(
            subject_id=data.subject_id,
            topic_id=data.topic_id,
            difficulty=data.difficulty.value,
            type="mcq",
            question_text=data.question_text,
            explanation=data.explanation,
            xp_value=xp_value,
            is_active=True,
            created_by=data.created_by,
        )

        options_data = [opt.model_dump() for opt in data.options]
        return self._repo.create_question(db, question, options_data)

    def get_question_by_id(self, db: Session, question_id: int) -> Question:
        """Retrieve a question or raise 404."""
        question = self._repo.get_question_by_id(db, question_id)
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")
        return question

    def get_questions(self, db: Session, filters: QuestionFilter, skip: int = 0, limit: int = 50) -> list[Question]:
        """List questions with optional filtering."""
        return self._repo.get_questions(db, filters, skip, limit)

    # --- Private validation helpers ---

    def _validate_admin_exists(self, db: Session, admin_id: int) -> None:
        if db.query(Admin).filter(Admin.id == admin_id).first() is None:
            raise HTTPException(status_code=400, detail=f"Admin with id {admin_id} does not exist")

    def _validate_subject_exists(self, db: Session, subject_id: int) -> None:
        if db.query(Subject).filter(Subject.id == subject_id).first() is None:
            raise HTTPException(status_code=400, detail=f"Subject with id {subject_id} does not exist")

    def _validate_topic_exists(self, db: Session, topic_id: int) -> None:
        if db.query(Topic).filter(Topic.id == topic_id).first() is None:
            raise HTTPException(status_code=400, detail=f"Topic with id {topic_id} does not exist")


# Singleton instance for dependency injection
question_service = QuestionService(repository=question_repository)
