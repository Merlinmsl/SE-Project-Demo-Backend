from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.question import Question, QuestionOption
from app.models.quiz_session import QuizSession, QuizSessionQuestion
from app.models.quiz_attempt import QuizAttempt
from app.models.student_stats import StudentSubjectStats, StudentTopicStats
from app.models.student import Student
from app.models.subject import Subject
from app.models.topic import Topic


class QuizRepository:
    """Data access layer for quiz generation and session management."""

    # --- Lookup helpers ---

    def get_student_by_id(self, db: Session, student_id: int) -> Student | None:
        return db.query(Student).filter(Student.id == student_id).first()

    def get_subject_by_id(self, db: Session, subject_id: int) -> Subject | None:
        return db.query(Subject).filter(Subject.id == subject_id).first()

    def get_topic_by_id(self, db: Session, topic_id: int) -> Topic | None:
        return db.query(Topic).filter(Topic.id == topic_id).first()

    def get_topics_for_subject(self, db: Session, subject_id: int) -> list[Topic]:
        return db.query(Topic).filter(Topic.subject_id == subject_id).all()

    # --- Stats ---

    def get_student_subject_stats(self, db: Session, student_id: int, subject_id: int) -> StudentSubjectStats | None:
        return (
            db.query(StudentSubjectStats)
            .filter(
                StudentSubjectStats.student_id == student_id,
                StudentSubjectStats.subject_id == subject_id,
            )
            .first()
        )

    def get_student_topic_stats(self, db: Session, student_id: int, topic_ids: list[int]) -> list[StudentTopicStats]:
        """Get topic stats for a student across multiple topics."""
        if not topic_ids:
            return []
        return (
            db.query(StudentTopicStats)
            .filter(
                StudentTopicStats.student_id == student_id,
                StudentTopicStats.topic_id.in_(topic_ids),
            )
            .all()
        )

    # --- Recent question exclusion ---

    def get_recent_question_ids(self, db: Session, student_id: int, subject_id: int, session_limit: int = 3) -> list[int]:
        """Get question IDs from the student's last N quiz sessions in this subject."""
        recent_sessions = (
            db.query(QuizSession.id)
            .filter(
                QuizSession.student_id == student_id,
                QuizSession.subject_id == subject_id,
            )
            .order_by(QuizSession.started_at.desc())
            .limit(session_limit)
            .subquery()
        )

        rows = (
            db.query(QuizSessionQuestion.question_id)
            .filter(QuizSessionQuestion.quiz_session_id.in_(db.query(recent_sessions.c.id)))
            .all()
        )
        return [r[0] for r in rows]

    # --- Question fetching ---

    def get_available_questions(
        self,
        db: Session,
        subject_id: int,
        difficulty: str,
        topic_ids: list[int] | None = None,
        exclude_ids: list[int] | None = None,
        limit: int = 15,
    ) -> list[Question]:
        """
        Fetch active questions filtered by subject, difficulty, optional topics,
        and excluding recently attempted questions. Results are randomized.
        """
        query = (
            db.query(Question)
            .options(joinedload(Question.options))
            .filter(
                Question.subject_id == subject_id,
                Question.difficulty == difficulty,
                Question.is_active == True,
            )
        )

        if topic_ids:
            query = query.filter(Question.topic_id.in_(topic_ids))

        if exclude_ids:
            query = query.filter(Question.id.notin_(exclude_ids))

        # Randomize selection
        query = query.order_by(func.random())

        return query.limit(limit).all()

    # --- Session creation ---

    def create_quiz_session(
        self,
        db: Session,
        student_id: int,
        subject_id: int,
        topic_id: int | None,
        mode: str,
        difficulty_profile: str,
        question_ids: list[int],
    ) -> int:
        """Create a quiz session and link questions. Returns session ID."""
        session = QuizSession(
            student_id=student_id,
            subject_id=subject_id,
            topic_id=topic_id,
            mode=mode,
            difficulty_profile=difficulty_profile,
        )
        db.add(session)
        db.flush()

        for q_id in question_ids:
            link = QuizSessionQuestion(
                quiz_session_id=session.id,
                question_id=q_id,
            )
            db.add(link)

        db.commit()
        db.refresh(session)
        return session.id


# Singleton instance
quiz_repository = QuizRepository()
