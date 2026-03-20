"""
Student dashboard statistics endpoint.

Returns real, per-student data (total XP, quizzes taken, per-subject scores)
so the frontend dashboard shows truthful information.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.dependencies import get_current_user
from app.core.security import AuthUser
from app.db.session import get_db
from app.repositories.student_repo import StudentRepository
from app.schemas.question import get_level_for_xp
from app.models.student_stats import StudentSubjectStats
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_answer import QuizAnswer
from app.models.quiz_session import QuizSession
from app.models.question import Question
from app.models.subject import Subject

router = APIRouter(prefix="/me", tags=["me"])


# ─── Response schemas ──────────────────────────────────────────────────────────

class SubjectStatOut(BaseModel):
    subject_id: int
    subject_name: str
    total_quizzes: int
    average_score: float
    total_xp: int


class RecentQuizOut(BaseModel):
    subject_name: str
    score_percentage: float
    xp_earned: int
    total_correct: int
    total_questions: int
    completed_at: str  # ISO format


class LevelOut(BaseModel):
    level: int
    level_name: str
    xp_to_next_level: int
    progress_percentage: float


class DashboardStatsOut(BaseModel):
    total_xp: int
    current_level: LevelOut
    total_quizzes: int
    average_score: float | None  # weighted average across subjects, None if no quizzes
    subject_stats: list[SubjectStatOut]
    recent_quizzes: list[RecentQuizOut]


# ─── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/dashboard-stats", response_model=DashboardStatsOut)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return real dashboard statistics for the authenticated student."""
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # ── Per-subject stats ──
    rows = (
        db.query(StudentSubjectStats, Subject.name)
        .join(Subject, Subject.id == StudentSubjectStats.subject_id)
        .filter(StudentSubjectStats.student_id == student.id)
        .all()
    )

    subject_stats: list[SubjectStatOut] = []
    total_xp = 0
    total_quizzes = 0
    weighted_score_sum = 0.0
    weight_sum = 0

    for stat, subj_name in rows:
        subject_stats.append(SubjectStatOut(
            subject_id=stat.subject_id,
            subject_name=subj_name,
            total_quizzes=stat.total_quizzes,
            average_score=float(stat.average_score),
            total_xp=stat.total_xp,
        ))
        total_xp += stat.total_xp
        total_quizzes += stat.total_quizzes
        weighted_score_sum += float(stat.average_score) * stat.total_quizzes
        weight_sum += stat.total_quizzes

    average_score = round(weighted_score_sum / weight_sum, 1) if weight_sum > 0 else None

    # ── Recent quiz attempts (last 5) ──
    recent = (
        db.query(QuizAttempt, Subject.name)
        .join(Subject, Subject.id == QuizAttempt.subject_id)
        .filter(QuizAttempt.student_id == student.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(5)
        .all()
    )

    recent_quizzes = [
        RecentQuizOut(
            subject_name=subj_name,
            score_percentage=float(attempt.score_percentage) if attempt.score_percentage else 0,
            xp_earned=attempt.xp_earned or 0,
            total_correct=attempt.total_correct or 0,
            total_questions=attempt.total_questions or 0,
            completed_at=attempt.completed_at.isoformat() if attempt.completed_at else "",
        )
        for attempt, subj_name in recent
    ]

    level_info = get_level_for_xp(total_xp)

    return DashboardStatsOut(
        total_xp=total_xp,
        current_level=LevelOut(**level_info),
        total_quizzes=total_quizzes,
        average_score=average_score,
        subject_stats=subject_stats,
        recent_quizzes=recent_quizzes,
    )


# ─── XP Summary ──────────────────────────────────────────────────────────────

class SubjectXpOut(BaseModel):
    subject_id: int
    subject_name: str
    total_xp: int


class RecentXpGainOut(BaseModel):
    question_id: int
    question_text: str
    difficulty: str
    is_correct: bool
    xp_earned: int
    bonus_xp: int
    subject_name: str
    completed_at: str


class XpSummaryOut(BaseModel):
    total_xp: int
    total_bonus_xp: int
    total_correct_answers: int
    xp_per_subject: list[SubjectXpOut]
    recent_xp_gains: list[RecentXpGainOut]


@router.get("/xp-summary", response_model=XpSummaryOut)
def get_xp_summary(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return XP breakdown for the authenticated student."""
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # ── Total XP, bonus XP, and correct answers across all quiz answers ──
    totals = (
        db.query(
            func.coalesce(func.sum(QuizAnswer.xp_earned), 0),
            func.coalesce(func.sum(QuizAnswer.bonus_xp), 0),
            func.count(QuizAnswer.id).filter(QuizAnswer.is_correct == True),
        )
        .join(QuizSession, QuizSession.id == QuizAnswer.quiz_session_id)
        .filter(QuizSession.student_id == student.id)
        .first()
    )
    total_xp = int(totals[0])
    total_bonus_xp = int(totals[1])
    total_correct_answers = int(totals[2])

    # ── XP per subject ──
    subject_rows = (
        db.query(
            Subject.id,
            Subject.name,
            func.coalesce(func.sum(QuizAnswer.xp_earned), 0),
        )
        .join(QuizSession, QuizSession.subject_id == Subject.id)
        .join(QuizAnswer, QuizAnswer.quiz_session_id == QuizSession.id)
        .filter(QuizSession.student_id == student.id)
        .group_by(Subject.id, Subject.name)
        .all()
    )
    xp_per_subject = [
        SubjectXpOut(subject_id=sid, subject_name=sname, total_xp=int(sxp))
        for sid, sname, sxp in subject_rows
    ]

    # ── Recent XP gains (last 10 correct answers) ──
    recent_rows = (
        db.query(QuizAnswer, Question, Subject.name, QuizSession.ended_at)
        .join(Question, Question.id == QuizAnswer.question_id)
        .join(QuizSession, QuizSession.id == QuizAnswer.quiz_session_id)
        .join(Subject, Subject.id == QuizSession.subject_id)
        .filter(
            QuizSession.student_id == student.id,
            QuizAnswer.is_correct == True,
            QuizAnswer.xp_earned > 0,
        )
        .order_by(QuizSession.ended_at.desc())
        .limit(10)
        .all()
    )
    recent_xp_gains = [
        RecentXpGainOut(
            question_id=ans.question_id,
            question_text=q.question_text,
            difficulty=q.difficulty,
            is_correct=True,
            xp_earned=ans.xp_earned,
            bonus_xp=ans.bonus_xp,
            subject_name=subj_name,
            completed_at=ended.isoformat() if ended else "",
        )
        for ans, q, subj_name, ended in recent_rows
    ]

    return XpSummaryOut(
        total_xp=total_xp,
        total_bonus_xp=total_bonus_xp,
        total_correct_answers=total_correct_answers,
        xp_per_subject=xp_per_subject,
        recent_xp_gains=recent_xp_gains,
    )
