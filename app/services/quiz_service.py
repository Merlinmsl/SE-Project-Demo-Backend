import random
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.question import Question
from app.schemas.quiz import (
    QuizStartRequest, QuizStartResponse, QuizQuestion, QuizQuestionOption,
    QuizSubmitRequest, QuizSubmitResponse, QuizQuestionResult
)
from app.repositories.quiz_repository import QuizRepository, quiz_repository
from app.models.quiz_attempt import QuizAttempt
from datetime import datetime, timezone


class QuizService:
    """Business logic for adaptive quiz generation."""

    def __init__(self, repository: QuizRepository):
        self._repo = repository

    def start_quiz(self, db: Session, data: QuizStartRequest) -> QuizStartResponse:
        """Generate a personalized quiz for the student."""

        # 1. Validate inputs
        self._validate_student(db, data.student_id)
        self._validate_subject(db, data.subject_id)
        if data.mode == "topic":
            self._validate_topic(db, data.topic_id, data.subject_id)

        # 2. Determine difficulty profile
        profile, distribution = self._determine_difficulty_profile(db, data.student_id, data.subject_id)

        # 3. Determine which topics to pull from
        topic_ids = self._resolve_topic_ids(db, data)

        # 4. Get recently attempted question IDs to exclude
        exclude_ids = self._repo.get_recent_question_ids(
            db, data.student_id, data.subject_id, RECENT_SESSION_EXCLUSION
        )

        # 5. Select questions per difficulty tier
        selected_questions = self._select_questions(
            db, data.subject_id, topic_ids, distribution, exclude_ids
        )

        if not selected_questions:
            raise HTTPException(
                status_code=404,
                detail="Not enough questions available to generate a quiz"
            )

        # 6. Lock into quiz session
        question_ids = [q.id for q in selected_questions]
        session_id = self._repo.create_quiz_session(
            db=db,
            student_id=data.student_id,
            subject_id=data.subject_id,
            topic_id=data.topic_id if data.mode == "topic" else None,
            mode=data.mode.value,
            difficulty_profile=profile,
            question_ids=question_ids,
        )

        # 7. Build response (WITHOUT is_correct)
        quiz_questions = self._build_quiz_response(selected_questions)

        return QuizStartResponse(
            session_id=session_id,
            mode=data.mode,
            difficulty_profile=profile,
            total_questions=len(quiz_questions),
            questions=quiz_questions,
        )


    # --- Topic resolution ---

    def _resolve_topic_ids(self, db: Session, data: QuizStartRequest) -> list[int]:
        """
        Topic mode: return only the selected topic.
        Term mode: return all topics for the subject, weighted by weakness.
        """
        if data.mode == "topic":
            return [data.topic_id]

        # Term mode — get all topics for the subject
        topics = self._repo.get_topics_for_subject(db, data.subject_id)
        if not topics:
            raise HTTPException(status_code=404, detail="No topics found for this subject")

        all_topic_ids = [t.id for t in topics]

        # Get student's topic stats to identify weak topics
        topic_stats = self._repo.get_student_topic_stats(db, data.student_id, all_topic_ids)
        stats_map = {ts.topic_id: float(ts.accuracy_percentage) for ts in topic_stats}

        # Topics without stats are treated as weakest (0% accuracy)
        # Sort topics by accuracy ascending (weakest first)
        sorted_topics = sorted(
            all_topic_ids,
            key=lambda tid: stats_map.get(tid, 0.0)
        )

        return sorted_topics

    # --- Question selection ---

    def _select_questions(
        self,
        db: Session,
        subject_id: int,
        topic_ids: list[int],
        distribution: dict[str, int],
        exclude_ids: list[int],
    ) -> list[Question]:
        """Select questions per difficulty tier, filling as many as possible."""
        selected = []

        for difficulty, count in distribution.items():
            questions = self._repo.get_available_questions(
                db=db,
                subject_id=subject_id,
                difficulty=difficulty,
                topic_ids=topic_ids,
                exclude_ids=exclude_ids,
                limit=count,
            )
            selected.extend(questions)

        # Shuffle the final set so difficulties are mixed
        random.shuffle(selected)
        return selected

    # --- Response builder ---

    def _build_quiz_response(self, questions: list[Question]) -> list[QuizQuestion]:
        """Convert Question models to response schemas WITHOUT is_correct."""
        result = []
        for q in questions:
            options = [
                QuizQuestionOption(id=opt.id, option_text=opt.option_text)
                for opt in q.options
            ]
            # Shuffle options so correct answer isn't always in the same position
            random.shuffle(options)

            result.append(QuizQuestion(
                id=q.id,
                question_text=q.question_text,
                difficulty=q.difficulty,
                options=options,
            ))
        return result

    # --- Validation helpers ---

    def _validate_student(self, db: Session, student_id: int) -> None:
        if self._repo.get_student_by_id(db, student_id) is None:
            raise HTTPException(status_code=400, detail=f"Student with id {student_id} does not exist")

    def _validate_subject(self, db: Session, subject_id: int) -> None:
        if self._repo.get_subject_by_id(db, subject_id) is None:
            raise HTTPException(status_code=400, detail=f"Subject with id {subject_id} does not exist")

    def _validate_topic(self, db: Session, topic_id: int, subject_id: int) -> None:
        topic = self._repo.get_topic_by_id(db, topic_id)
        if topic is None:
            raise HTTPException(status_code=400, detail=f"Topic with id {topic_id} does not exist")
        if topic.subject_id != subject_id:
            raise HTTPException(
                status_code=400,
                detail=f"Topic {topic_id} does not belong to subject {subject_id}"
            )


    def submit_quiz(self, db: Session, data: QuizSubmitRequest) -> QuizSubmitResponse:
        session = self._repo.get_quiz_session(db, data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Quiz session not found")
            
        if session.status == "completed":
            raise HTTPException(status_code=400, detail="Quiz session already completed")
            
        questions = self._repo.get_session_questions_with_options(db, data.session_id)
        question_map = {q.id: q for q in questions}
        
        total_correct = 0
        total_xp = 0
        topic_results = {}
        processed_answers = []
        detailed_results = []
        
        for ans in data.answers:
            question = question_map.get(ans.question_id)
            if not question:
                continue
                
            is_correct = False
            correct_option_id = 0
            for opt in question.options:
                if opt.is_correct:
                    correct_option_id = opt.id
                if opt.id == ans.selected_option_id and opt.is_correct:
                    is_correct = True
                    # Do not break immediately so we can still find the correct_option_id if needed
                    
            if is_correct:
                total_correct += 1
                total_xp += (question.xp_value or 10)
                
            topic_results[question.topic_id] = is_correct
            
            detailed_results.append(
                QuizQuestionResult(
                    question_id=ans.question_id,
                    is_correct=is_correct,
                    correct_option_id=correct_option_id
                )
            )
            
            processed_answers.append({
                "question_id": ans.question_id,
                "selected_option_id": ans.selected_option_id,
                "is_correct": is_correct
            })
            
        total_questions = len(questions)
        score_percentage = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        attempt = QuizAttempt(
            quiz_session_id=session.id,
            student_id=session.student_id,
            subject_id=session.subject_id,
            score_percentage=score_percentage,
            total_correct=total_correct,
            total_questions=total_questions,
            xp_earned=total_xp,
            completed_at=datetime.now(timezone.utc)
        )
        
        # Save submission to DB
        self._repo.save_quiz_submission(db, attempt, processed_answers)
        
        # Update session status
        session.status = "completed"
        session.ended_at = datetime.now(timezone.utc)
        db.commit()
        
        # Update global stats
        self._repo.update_student_stats(
            db, 
            student_id=session.student_id, 
            subject_id=session.subject_id, 
            score=score_percentage, 
            xp=total_xp, 
            topic_results=topic_results
        )
        
        is_beginner = session.difficulty_profile == "beginner"
        
        return QuizSubmitResponse(
            score_percentage=score_percentage,
            xp_earned=total_xp,
            total_correct=total_correct,
            total_questions=total_questions,
            is_beginner=is_beginner,
            results=detailed_results
        )

# Singleton instance
quiz_service = QuizService(repository=quiz_repository)
