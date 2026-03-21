from sqlalchemy.orm import Session, selectinload
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
            .options(selectinload(Question.options))
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
    # --- Session fetching ---

    def get_quiz_session(self, db: Session, session_id: int) -> QuizSession | None:
        return db.query(QuizSession).filter(QuizSession.id == session_id).first()

    def get_session_questions_with_options(self, db: Session, session_id: int) -> list[Question]:
        """Fetch the questions assigned to a quiz session, including their options to eval answers."""
        rows = db.query(QuizSessionQuestion.question_id).filter(QuizSessionQuestion.quiz_session_id == session_id).all()
        q_ids = [r[0] for r in rows]

        return db.query(Question).options(selectinload(Question.options)).filter(Question.id.in_(q_ids)).all()

    # --- Submission and stats updates ---
    def save_quiz_submission(self, db: Session, attempt: QuizAttempt, answers: list[dict]):
        """Save attempt and detailed answers together."""
        from app.models.quiz_answer import QuizAnswer

        db.add(attempt)
        db.flush()

        # Save individual answers with per-answer XP and bonus
        for ans in answers:
            db.add(QuizAnswer(
                quiz_session_id=attempt.quiz_session_id,
                question_id=ans["question_id"],
                selected_option_id=ans["selected_option_id"],
                is_correct=ans["is_correct"],
                xp_earned=ans.get("xp_earned", 0),
                bonus_xp=ans.get("bonus_xp", 0),
            ))

    def update_student_stats(self, db: Session, student_id: int, subject_id: int, score: float, xp: int, topic_results: dict[int, bool]):
        """Update subject and topic level statistics based on quiz results."""
        # 1. Subject Stats
        subject_stats = self.get_student_subject_stats(db, student_id, subject_id)
        if not subject_stats:
            subject_stats = StudentSubjectStats(
                student_id=student_id,
                subject_id=subject_id,
                total_quizzes=1,
                average_score=score,
                total_xp=xp
            )
            db.add(subject_stats)
        else:
            # Rolling average
            old_total = subject_stats.average_score * subject_stats.total_quizzes
            subject_stats.total_quizzes += 1
            subject_stats.average_score = (old_total + score) / subject_stats.total_quizzes
            subject_stats.total_xp += xp

        # 2. Topic Stats
        for topic_id, is_correct in topic_results.items():
            topic_stat = db.query(StudentTopicStats).filter(
                StudentTopicStats.student_id == student_id,
                StudentTopicStats.topic_id == topic_id
            ).first()

            if not topic_stat:
                topic_stat = StudentTopicStats(
                    student_id=student_id,
                    topic_id=topic_id,
                    attempt_count=1,
                    correct_count=1 if is_correct else 0,
                    accuracy_percentage=100.0 if is_correct else 0.0
                )
                db.add(topic_stat)
            else:
                topic_stat.attempt_count += 1
                if is_correct:
                    topic_stat.correct_count += 1
                topic_stat.accuracy_percentage = (topic_stat.correct_count / topic_stat.attempt_count) * 100

        db.commit()

    def update_study_streak(self, db: Session, student_id: int) -> int:
        """Update the student's study streak and return the new current streak."""
        from app.models.study_streak import StudyStreak
        from datetime import date, timedelta

        today = date.today()
        streak = db.query(StudyStreak).filter(StudyStreak.student_id == student_id).first()

        if not streak:
            streak = StudyStreak(
                student_id=student_id,
                current_streak=1,
                longest_streak=1,
                last_activity_date=today,
            )
            db.add(streak)
            db.commit()
            return 1

        # Already logged activity today
        if streak.last_activity_date == today:
            return streak.current_streak

        yesterday = today - timedelta(days=1)

        if streak.last_activity_date == yesterday:
            streak.current_streak += 1
        else:
            # Streak broken — reset to 1
            streak.current_streak = 1

        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

        streak.last_activity_date = today
        db.commit()
        return streak.current_streak


# Singleton instance
quiz_repository = QuizRepository()

