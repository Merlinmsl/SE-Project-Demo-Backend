from sqlalchemy.orm import Session, joinedload
from app.models.question import Question, QuestionOption
from app.schemas.question import QuestionCreate, QuestionFilter


class QuestionRepository:
    """Data access layer for questions and question options."""

    def create_question(self, db: Session, question: Question, options_data: list[dict]) -> Question:
        """Insert a question and its options in a single transaction."""
        db.add(question)
        db.flush()  # Get the question ID before inserting options

        for opt_data in options_data:
            option = QuestionOption(
                question_id=question.id,
                option_text=opt_data["option_text"],
                is_correct=opt_data["is_correct"],
            )
            db.add(option)

        db.commit()
        db.refresh(question)
        return question

    def get_question_by_id(self, db: Session, question_id: int) -> Question | None:
        """Fetch a single question with its options eagerly loaded."""
        return (
            db.query(Question)
            .options(joinedload(Question.options))
            .filter(Question.id == question_id)
            .first()
        )

    def get_questions(self, db: Session, filters: QuestionFilter, skip: int = 0, limit: int = 50) -> list[Question]:
        """List questions with optional filtering."""
        query = db.query(Question).options(joinedload(Question.options))

        if filters.subject_id is not None:
            query = query.filter(Question.subject_id == filters.subject_id)
        if filters.topic_id is not None:
            query = query.filter(Question.topic_id == filters.topic_id)
        if filters.difficulty is not None:
            query = query.filter(Question.difficulty == filters.difficulty.value)
        if filters.is_active is not None:
            query = query.filter(Question.is_active == filters.is_active)

        return query.offset(skip).limit(limit).all()


# Singleton instance for dependency injection
question_repository = QuestionRepository()
