import random
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.question import Question
from app.schemas.quiz import (
    QuizStartRequest, QuizStartResponse, QuizQuestion, QuizQuestionOption,
    QuizSubmitRequest, QuizSubmitResponse, AnswerResult, NewlyEarnedBadge
)
from app.schemas.question import XP_BONUS, PERFECT_SCORE_BONUS, DifficultyLevel, get_streak_bonus
from app.repositories.quiz_repository import QuizRepository, quiz_repository
from app.services.streak_badge_service import StreakBadgeService
from app.models.quiz_attempt import QuizAttempt
from app.services.badge_service import badge_service
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# --- Difficulty distributions (easy, medium, hard) ---
BEGINNER_DISTRIBUTION = {"easy": 8, "medium": 4, "hard": 3}  # total = 15

ADAPTIVE_PROFILES = {
    "low":      {"easy": 9, "medium": 4, "hard": 2},   # avg 0-40
    "medium":   {"easy": 5, "medium": 6, "hard": 4},   # avg 41-60
    "high":     {"easy": 3, "medium": 6, "hard": 6},   # avg 61-80
    "advanced": {"easy": 2, "medium": 4, "hard": 9},   # avg 81-100
}

BEGINNER_THRESHOLD = 5  # quizzes before switching to adaptive
RECENT_SESSION_EXCLUSION = 3  # exclude questions from last N sessions


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

    # --- Adaptive difficulty profiling ---

    def _determine_difficulty_profile(
        self, db: Session, student_id: int, subject_id: int
    ) -> tuple[str, dict]:
        """
        Returns (profile_name, distribution_dict).
        Beginners (<5 quizzes) get a protective distribution.
        Others get a profile based on their average score.
        """
        stats = self._repo.get_student_subject_stats(db, student_id, subject_id)

        if stats is None or stats.total_quizzes < BEGINNER_THRESHOLD:
            return "beginner", BEGINNER_DISTRIBUTION.copy()

        avg = float(stats.average_score)

        if avg <= 40:
            profile = "low"
        elif avg <= 60:
            profile = "medium"
        elif avg <= 80:
            profile = "high"
        else:
            profile = "advanced"

        return profile, ADAPTIVE_PROFILES[profile].copy()

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
                topic_id=q.topic.id,
                topic_name=q.topic.name,
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
                    
            answer_xp = 0
            bonus_xp = 0
            if is_correct:
                total_correct += 1
                base_xp = question.xp_value or 10
                difficulty_key = DifficultyLevel(question.difficulty)
                bonus_xp = XP_BONUS.get(difficulty_key, 0)
                answer_xp = base_xp + bonus_xp
                total_xp += answer_xp

            topic_results[question.topic_id] = is_correct

            processed_answers.append({
                "question_id": ans.question_id,
                "selected_option_id": ans.selected_option_id,
                "is_correct": is_correct,
                "xp_earned": answer_xp,
                "bonus_xp": bonus_xp,
                "correct_option_id": correct_option_id,
            })
            
        total_questions = len(questions)
        score_percentage = (total_correct / total_questions * 100) if total_questions > 0 else 0

        # Award bonus XP for getting every question right
        is_perfect_score = total_questions > 0 and total_correct == total_questions
        completion_bonus_xp = PERFECT_SCORE_BONUS if is_perfect_score else 0
        total_xp += completion_bonus_xp

        # Update study streak and award streak bonus XP
        current_streak = self._repo.update_study_streak(db, session.student_id)
        streak_bonus_xp = get_streak_bonus(current_streak)
        total_xp += streak_bonus_xp

        # ── Streak update ──
        new_streak, days_gap = self._repo.update_study_streak(db, session.student_id)
        current_streak = new_streak

        # ── Milestone & Badge evaluation ──
        # 1. 7-day streak badge (original logic)
        streak_badge_service = StreakBadgeService(db)
        streak_result = streak_badge_service.check_and_award(session.student_id)
        
        # 2. General Milestones (Quiz counts, XP, Time, Inactivity)
        newly_earned_badge_objects = badge_service.evaluate_milestones(db, session.student_id, days_gap)

        # 3. Combine newly earned badges for response
        final_earned_badges = []
        
        # Add streak badge if newly awarded
        if streak_result.newly_awarded:
            final_earned_badges.append(NewlyEarnedBadge(
                badge_id=streak_result.badge_id,
                badge_name=streak_result.badge_name,
                image_url=streak_result.image_url
            ))
            
        # Add milestone badges
        for b in newly_earned_badge_objects:
            final_earned_badges.append(NewlyEarnedBadge(
                badge_id=b["badge_id"],
                badge_name=b["badge_name"],
                image_url=b["image_url"]
            ))

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

        # ── Evaluate district ranking and auto-award badge (MIN-62) ──
        try:
            # Re-fetch or use a shared badge service if needed, but for now use the original
            badge_service.evaluate_district_ranking(db, session.student_id)
        except Exception as exc:
            # Badge evaluation should never block quiz submission
            logger.warning("District badge evaluation failed for student %s: %s", session.student_id, exc)
        
        is_beginner = session.difficulty_profile == "beginner"

        answer_results = [
            AnswerResult(
                question_id=ans["question_id"],
                is_correct=ans["is_correct"],
                xp_earned=ans["xp_earned"],
                bonus_xp=ans["bonus_xp"],
                correct_option_id=ans["correct_option_id"],
                selected_option_id=ans["selected_option_id"],
            )
            for ans in processed_answers
        ]

        total_bonus_xp = sum(ans["bonus_xp"] for ans in processed_answers)

        return QuizSubmitResponse(
            score_percentage=score_percentage,
            xp_earned=total_xp,
            total_bonus_xp=total_bonus_xp,
            completion_bonus_xp=completion_bonus_xp,
            streak_bonus_xp=streak_bonus_xp,
            current_streak=current_streak,
            is_perfect_score=is_perfect_score,
            total_correct=total_correct,
            total_questions=total_questions,
            is_beginner=is_beginner,
            answer_results=answer_results,
            newly_earned_badges=final_earned_badges,
        )

# Singleton instance
quiz_service = QuizService(repository=quiz_repository)
