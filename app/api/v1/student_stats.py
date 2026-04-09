"""
Student dashboard statistics endpoint.

Returns real, per-student data (total XP, quizzes taken, per-subject scores)
so the frontend dashboard shows truthful information.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.dependencies import get_current_user
from app.core.security import AuthUser
from app.db.session import get_db
from app.repositories.student_repo import StudentRepository
from app.repositories.badge_repo import BadgeRepository
from app.schemas.question import get_level_for_xp
from app.schemas.badge import StudentBadgeOut, StudentBadgesListOut
from app.services.streak_badge_service import STREAK_7_BADGE_NAME
from app.models.student_stats import StudentSubjectStats
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_answer import QuizAnswer
from app.models.quiz_session import QuizSession
from app.models.question import Question
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.student_stats import StudentTopicStats
from app.models.study_streak import StudyStreak
from app.models.student import Student
from app.models.district import District
from app.models.province import Province
from app.models.badge import Badge

router = APIRouter(prefix="/me", tags=["me"])


# ─── Response schemas ──────────────────────────────────────────────────────────

class SubjectStatOut(BaseModel):
    subject_id: int
    subject_name: str
    total_quizzes: int
    average_score: float
    total_xp: int


class RecentQuizOut(BaseModel):
    attempt_id: int
    session_id: int
    subject_name: str
    subject_id: int
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
            attempt_id=attempt.id,
            session_id=attempt.quiz_session_id,
            subject_name=subj_name,
            subject_id=attempt.subject_id,
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


# ─── Subject Progress Bars ───────────────────────────────────────────────────

class TopicProgressOut(BaseModel):
    topic_id: int
    topic_name: str
    attempted: bool
    accuracy_percentage: float


class SubjectProgressOut(BaseModel):
    subject_id: int
    subject_name: str
    total_topics: int
    topics_attempted: int
    progress_percentage: float
    average_accuracy: float
    total_quizzes: int
    total_xp: int
    topics: list[TopicProgressOut]


@router.get("/subject-progress", response_model=list[SubjectProgressOut])
def get_subject_progress(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return per-subject progress bars showing topic coverage and accuracy."""
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # Get all subjects with their topics
    subjects = db.query(Subject).all()

    # Get student's topic stats in one query
    topic_stats = (
        db.query(StudentTopicStats)
        .filter(StudentTopicStats.student_id == student.id)
        .all()
    )
    topic_stats_map = {ts.topic_id: ts for ts in topic_stats}

    # Get student's subject stats in one query
    subject_stats = (
        db.query(StudentSubjectStats)
        .filter(StudentSubjectStats.student_id == student.id)
        .all()
    )
    subject_stats_map = {ss.subject_id: ss for ss in subject_stats}

    result = []
    for subject in subjects:
        topics = db.query(Topic).filter(Topic.subject_id == subject.id).all()
        total_topics = len(topics)

        topic_progress = []
        topics_attempted = 0
        accuracy_sum = 0.0

        for topic in topics:
            ts = topic_stats_map.get(topic.id)
            attempted = ts is not None and ts.attempt_count > 0
            accuracy = float(ts.accuracy_percentage) if ts else 0.0

            if attempted:
                topics_attempted += 1
                accuracy_sum += accuracy

            topic_progress.append(TopicProgressOut(
                topic_id=topic.id,
                topic_name=topic.name,
                attempted=attempted,
                accuracy_percentage=round(accuracy, 1),
            ))

        progress_pct = round((topics_attempted / total_topics) * 100, 1) if total_topics > 0 else 0.0
        avg_accuracy = round(accuracy_sum / topics_attempted, 1) if topics_attempted > 0 else 0.0

        ss = subject_stats_map.get(subject.id)

        result.append(SubjectProgressOut(
            subject_id=subject.id,
            subject_name=subject.name,
            total_topics=total_topics,
            topics_attempted=topics_attempted,
            progress_percentage=progress_pct,
            average_accuracy=avg_accuracy,
            total_quizzes=ss.total_quizzes if ss else 0,
            total_xp=ss.total_xp if ss else 0,
            topics=topic_progress,
        ))

    return result


# ─── Recent Quiz Summary ─────────────────────────────────────────────────────

class QuizAnswerSummaryOut(BaseModel):
    question_id: int
    question_text: str
    difficulty: str
    is_correct: bool
    xp_earned: int
    bonus_xp: int


class QuizSummaryOut(BaseModel):
    attempt_id: int
    session_id: int
    subject_name: str
    mode: str
    difficulty_profile: str
    score_percentage: float
    total_correct: int
    total_questions: int
    xp_earned: int
    completed_at: str
    answers: list[QuizAnswerSummaryOut]


@router.get("/recent-quizzes", response_model=list[QuizSummaryOut])
def get_recent_quizzes(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return the last 5 completed quizzes with full answer breakdowns."""
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # Fetch last 5 quiz attempts with subject and session info
    attempts = (
        db.query(QuizAttempt, Subject.name, QuizSession.mode, QuizSession.difficulty_profile)
        .join(Subject, Subject.id == QuizAttempt.subject_id)
        .join(QuizSession, QuizSession.id == QuizAttempt.quiz_session_id)
        .filter(QuizAttempt.student_id == student.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(5)
        .all()
    )

    result = []
    for attempt, subj_name, mode, diff_profile in attempts:
        # Get per-answer details for this attempt's session
        answers = (
            db.query(QuizAnswer, Question.question_text, Question.difficulty)
            .join(Question, Question.id == QuizAnswer.question_id)
            .filter(QuizAnswer.quiz_session_id == attempt.quiz_session_id)
            .all()
        )

        answer_summaries = [
            QuizAnswerSummaryOut(
                question_id=ans.question_id,
                question_text=q_text,
                difficulty=diff,
                is_correct=ans.is_correct or False,
                xp_earned=ans.xp_earned,
                bonus_xp=ans.bonus_xp,
            )
            for ans, q_text, diff in answers
        ]

        result.append(QuizSummaryOut(
            attempt_id=attempt.id,
            session_id=attempt.quiz_session_id,
            subject_name=subj_name,
            mode=mode,
            difficulty_profile=diff_profile,
            score_percentage=float(attempt.score_percentage) if attempt.score_percentage else 0,
            total_correct=attempt.total_correct or 0,
            total_questions=attempt.total_questions or 0,
            xp_earned=attempt.xp_earned or 0,
            completed_at=attempt.completed_at.isoformat() if attempt.completed_at else "",
            answers=answer_summaries,
        ))

    return result


# ─── Study Streak & Leaderboard Schemas ──────────────────────────────────────

class StudyStreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    last_activity_date: str | None
    has_7_day_badge: bool = False


class LeaderboardEntryOut(BaseModel):
    rank: int
    student_id: int
    username: str | None
    avatar_key: str | None
    total_xp: int
    is_current_user: bool


@router.get("/study-streak", response_model=StudyStreakOut)
def get_study_streak(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return the authenticated student's current and longest study streak."""
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    streak = db.query(StudyStreak).filter(StudyStreak.student_id == student.id).first()

    has_badge = False
    badge_repo = BadgeRepository()
    badge = badge_repo.get_badge_by_name(db, STREAK_7_BADGE_NAME)
    if badge:
        has_badge = badge_repo.has_badge(db, student.id, badge.id)

    if not streak:
        return StudyStreakOut(
            current_streak=0,
            longest_streak=0,
            last_activity_date=None,
            has_7_day_badge=has_badge,
        )

    return StudyStreakOut(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=streak.last_activity_date.isoformat() if streak.last_activity_date else None,
        has_7_day_badge=has_badge,
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntryOut])
def get_leaderboard(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return top 10 students ranked by total XP across all subjects."""
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # Aggregate total XP per student from subject stats
    rows = (
        db.query(
            StudentSubjectStats.student_id,
            func.sum(StudentSubjectStats.total_xp).label("total_xp"),
        )
        .group_by(StudentSubjectStats.student_id)
        .order_by(func.sum(StudentSubjectStats.total_xp).desc())
        .limit(10)
        .all()
    )

    # Get student details for the ranked students
    student_ids = [r.student_id for r in rows]
    students = (
        db.query(Student)
        .filter(Student.id.in_(student_ids))
        .all()
    ) if student_ids else []
    student_map = {s.id: s for s in students}

    result = []
    for rank, row in enumerate(rows, start=1):
        s = student_map.get(row.student_id)
        result.append(LeaderboardEntryOut(
            rank=rank,
            student_id=row.student_id,
            username=s.username if s else None,
            avatar_key=s.avatar_key if s else None,
            total_xp=int(row.total_xp),
            is_current_user=row.student_id == student.id,
        ))

    # If current user isn't in top 10, append their rank
    if student.id not in student_ids:
        user_xp_row = (
            db.query(func.coalesce(func.sum(StudentSubjectStats.total_xp), 0))
            .filter(StudentSubjectStats.student_id == student.id)
            .scalar()
        )
        user_total_xp = int(user_xp_row) if user_xp_row else 0

        # Count how many students have more XP
        rank = (
            db.query(func.count(StudentSubjectStats.student_id))
            .group_by(StudentSubjectStats.student_id)
            .having(func.sum(StudentSubjectStats.total_xp) > user_total_xp)
            .count()
        ) + 1

        result.append(LeaderboardEntryOut(
            rank=rank,
            student_id=student.id,
            username=student.username,
            avatar_key=student.avatar_key,
            total_xp=user_total_xp,
            is_current_user=True,
        ))

    return result


# ─── District Leaderboard ─────────────────────────────────────────────────────

class DistrictLeaderboardEntryOut(BaseModel):
    rank: int
    username: str | None
    total_xp: int
    is_current_user: bool


class DistrictLeaderboardOut(BaseModel):
    district_id: int
    district_name: str
    entries: list[DistrictLeaderboardEntryOut]


@router.get("/district-leaderboard", response_model=DistrictLeaderboardOut)
def get_district_leaderboard(
    district_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return top 10 students by total XP within a district.

    If district_id is omitted, defaults to the authenticated student's district.
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # Resolve district
    target_district_id = district_id if district_id is not None else student.district_id

    # Fetch district name
    district = db.query(District).filter(District.id == target_district_id).first()
    district_name = district.name if district else "Unknown"

    # Aggregate total XP per student in the district, top 10
    rows = (
        db.query(
            StudentSubjectStats.student_id,
            func.sum(StudentSubjectStats.total_xp).label("total_xp"),
        )
        .join(Student, Student.id == StudentSubjectStats.student_id)
        .filter(Student.district_id == target_district_id)
        .group_by(StudentSubjectStats.student_id)
        .order_by(func.sum(StudentSubjectStats.total_xp).desc())
        .limit(10)
        .all()
    )

    # Get student details for ranked students
    student_ids = [r.student_id for r in rows]
    students_in_list = (
        db.query(Student)
        .filter(Student.id.in_(student_ids))
        .all()
    ) if student_ids else []
    student_map = {s.id: s for s in students_in_list}

    entries: list[DistrictLeaderboardEntryOut] = []
    for rank, row in enumerate(rows, start=1):
        s = student_map.get(row.student_id)
        entries.append(DistrictLeaderboardEntryOut(
            rank=rank,
            username=s.username if s else None,
            total_xp=int(row.total_xp),
            is_current_user=row.student_id == student.id,
        ))

    # If viewing the student's own district and they're not in the top 10, append their rank
    if student.district_id == target_district_id and student.id not in student_ids:
        user_xp_row = (
            db.query(func.coalesce(func.sum(StudentSubjectStats.total_xp), 0))
            .filter(StudentSubjectStats.student_id == student.id)
            .scalar()
        )
        user_total_xp = int(user_xp_row) if user_xp_row else 0

        # Count how many students in this district have more XP
        user_rank = (
            db.query(StudentSubjectStats.student_id)
            .join(Student, Student.id == StudentSubjectStats.student_id)
            .filter(Student.district_id == target_district_id)
            .group_by(StudentSubjectStats.student_id)
            .having(func.sum(StudentSubjectStats.total_xp) > user_total_xp)
            .count()
        ) + 1

        entries.append(DistrictLeaderboardEntryOut(
            rank=user_rank,
            username=student.username,
            total_xp=user_total_xp,
            is_current_user=True,
        ))

    return DistrictLeaderboardOut(
        district_id=target_district_id,
        district_name=district_name,
        entries=entries,
    )


# ─── Province Leaderboard ─────────────────────────────────────────────────────

class ProvinceLeaderboardEntryOut(BaseModel):
    rank: int
    username: str | None
    total_xp: int
    is_current_user: bool


class ProvinceLeaderboardOut(BaseModel):
    province_id: int
    province_name: str
    entries: list[ProvinceLeaderboardEntryOut]


@router.get("/province-leaderboard", response_model=ProvinceLeaderboardOut)
def get_province_leaderboard(
    province_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return top 10 students by total XP within a province.

    If province_id is omitted, defaults to the authenticated student's province.
    """
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # Resolve province: student → district → province
    if province_id is not None:
        target_province_id = province_id
    elif student.district_id:
        district = db.query(District).filter(District.id == student.district_id).first()
        target_province_id = district.province_id if district else None
    else:
        target_province_id = None

    # Fetch province name
    province = db.query(Province).filter(Province.id == target_province_id).first() if target_province_id else None
    province_name = province.name if province else "Unknown"

    # Aggregate total XP per student in the province, top 10
    rows = (
        db.query(
            StudentSubjectStats.student_id,
            func.sum(StudentSubjectStats.total_xp).label("total_xp"),
        )
        .join(Student, Student.id == StudentSubjectStats.student_id)
        .join(District, District.id == Student.district_id)
        .filter(District.province_id == target_province_id)
        .group_by(StudentSubjectStats.student_id)
        .order_by(func.sum(StudentSubjectStats.total_xp).desc())
        .limit(10)
        .all()
    )

    # Get student details
    student_ids = [r.student_id for r in rows]
    students_in_list = (
        db.query(Student).filter(Student.id.in_(student_ids)).all()
    ) if student_ids else []
    student_map = {s.id: s for s in students_in_list}

    entries: list[ProvinceLeaderboardEntryOut] = []
    for rank, row in enumerate(rows, start=1):
        s = student_map.get(row.student_id)
        entries.append(ProvinceLeaderboardEntryOut(
            rank=rank,
            username=s.username if s else None,
            total_xp=int(row.total_xp),
            is_current_user=row.student_id == student.id,
        ))

    # If viewing the student's own province and they're not in top 10
    student_province_id = None
    if student.district_id:
        sd = db.query(District).filter(District.id == student.district_id).first()
        student_province_id = sd.province_id if sd else None

    if student_province_id == target_province_id and student.id not in student_ids:
        user_xp_row = (
            db.query(func.coalesce(func.sum(StudentSubjectStats.total_xp), 0))
            .filter(StudentSubjectStats.student_id == student.id)
            .scalar()
        )
        user_total_xp = int(user_xp_row) if user_xp_row else 0

        user_rank = (
            db.query(StudentSubjectStats.student_id)
            .join(Student, Student.id == StudentSubjectStats.student_id)
            .join(District, District.id == Student.district_id)
            .filter(District.province_id == target_province_id)
            .group_by(StudentSubjectStats.student_id)
            .having(func.sum(StudentSubjectStats.total_xp) > user_total_xp)
            .count()
        ) + 1

        entries.append(ProvinceLeaderboardEntryOut(
            rank=user_rank,
            username=student.username,
            total_xp=user_total_xp,
            is_current_user=True,
        ))

    return ProvinceLeaderboardOut(
        province_id=target_province_id or 0,
        province_name=province_name,
        entries=entries,
    )


# ─── National Leaderboard ─────────────────────────────────────────────────────

class NationalLeaderboardEntryOut(BaseModel):
    rank: int
    username: str | None
    total_xp: int
    is_current_user: bool


class NationalLeaderboardOut(BaseModel):
    entries: list[NationalLeaderboardEntryOut]


@router.get("/national-leaderboard", response_model=NationalLeaderboardOut)
def get_national_leaderboard(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return top 10 students by total XP nationally (all students)."""
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # Aggregate total XP per student, no geographic filter, top 10
    rows = (
        db.query(
            StudentSubjectStats.student_id,
            func.sum(StudentSubjectStats.total_xp).label("total_xp"),
        )
        .group_by(StudentSubjectStats.student_id)
        .order_by(func.sum(StudentSubjectStats.total_xp).desc())
        .limit(10)
        .all()
    )

    student_ids = [r.student_id for r in rows]
    students_in_list = (
        db.query(Student).filter(Student.id.in_(student_ids)).all()
    ) if student_ids else []
    student_map = {s.id: s for s in students_in_list}

    entries: list[NationalLeaderboardEntryOut] = []
    for rank, row in enumerate(rows, start=1):
        s = student_map.get(row.student_id)
        entries.append(NationalLeaderboardEntryOut(
            rank=rank,
            username=s.username if s else None,
            total_xp=int(row.total_xp),
            is_current_user=row.student_id == student.id,
        ))

    # If current user is not in top 10, append their rank
    if student.id not in student_ids:
        user_xp_row = (
            db.query(func.coalesce(func.sum(StudentSubjectStats.total_xp), 0))
            .filter(StudentSubjectStats.student_id == student.id)
            .scalar()
        )
        user_total_xp = int(user_xp_row) if user_xp_row else 0

        user_rank = (
            db.query(StudentSubjectStats.student_id)
            .group_by(StudentSubjectStats.student_id)
            .having(func.sum(StudentSubjectStats.total_xp) > user_total_xp)
            .count()
        ) + 1

        entries.append(NationalLeaderboardEntryOut(
            rank=user_rank,
            username=student.username,
            total_xp=user_total_xp,
            is_current_user=True,
        ))

    return NationalLeaderboardOut(entries=entries)


# ─── Subject-wise Leaderboard ─────────────────────────────────────────────────

class SubjectLeaderboardEntryOut(BaseModel):
    rank: int
    username: str | None
    total_xp: int
    is_current_user: bool


class SubjectLeaderboardOut(BaseModel):
    subject_id: int
    subject_name: str
    entries: list[SubjectLeaderboardEntryOut]


@router.get("/subject-leaderboard", response_model=SubjectLeaderboardOut)
def get_subject_leaderboard(
    subject_id: int = Query(...),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    """Return top 10 students by XP in a specific subject (national scope)."""
    st_repo = StudentRepository(db)
    student = st_repo.create_if_missing(user)

    # Fetch subject name
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    subject_name = subject.name if subject else "Unknown"

    # Top 10 students by XP in this subject
    rows = (
        db.query(
            StudentSubjectStats.student_id,
            StudentSubjectStats.total_xp,
        )
        .filter(StudentSubjectStats.subject_id == subject_id)
        .order_by(StudentSubjectStats.total_xp.desc())
        .limit(10)
        .all()
    )

    student_ids = [r.student_id for r in rows]
    students_in_list = (
        db.query(Student).filter(Student.id.in_(student_ids)).all()
    ) if student_ids else []
    student_map = {s.id: s for s in students_in_list}

    entries: list[SubjectLeaderboardEntryOut] = []
    for rank, row in enumerate(rows, start=1):
        s = student_map.get(row.student_id)
        entries.append(SubjectLeaderboardEntryOut(
            rank=rank,
            username=s.username if s else None,
            total_xp=int(row.total_xp),
            is_current_user=row.student_id == student.id,
        ))

    # If current user is not in top 10, append their rank
    if student.id not in student_ids:
        user_stats = (
            db.query(StudentSubjectStats)
            .filter(
                StudentSubjectStats.student_id == student.id,
                StudentSubjectStats.subject_id == subject_id,
            )
            .first()
        )
        user_total_xp = int(user_stats.total_xp) if user_stats else 0

        user_rank = (
            db.query(StudentSubjectStats.student_id)
            .filter(StudentSubjectStats.subject_id == subject_id)
            .filter(StudentSubjectStats.total_xp > user_total_xp)
            .count()
        ) + 1

        entries.append(SubjectLeaderboardEntryOut(
            rank=user_rank,
            username=student.username,
            total_xp=user_total_xp,
            is_current_user=True,
        ))

    return SubjectLeaderboardOut(
        subject_id=subject_id,
        subject_name=subject_name,
        entries=entries,
    )


# ─── Student Badges ───────────────────────────────────────────────────────────

@router.get(
    "/badges",
    response_model=StudentBadgesListOut,
    summary="List badges earned by the authenticated student",
    tags=["badges"],
)
def get_my_badges(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> StudentBadgesListOut:
    """Return all badges the authenticated student has earned (MIN-61).

    Each entry includes full badge metadata (name, description, image URL) so
    the frontend can render the badge card directly without a second request.
    Results are ordered newest-award-first.

    Returns
    -------
    StudentBadgesListOut
        ``total_count`` — total number of badges earned.
        ``badges``      — list of :class:`StudentBadgeOut` objects.
    """
    st_repo = StudentRepository(db)
    badge_repo = BadgeRepository()
    student = st_repo.create_if_missing(user)

    # Fetch all StudentBadge rows for this student (ordered newest first).
    student_badges = badge_repo.get_student_badges(db, student.id)

    if not student_badges:
        return StudentBadgesListOut(total_count=0, badges=[])

    # Bulk-fetch badge metadata in a single query to avoid N+1.
    badge_ids = [sb.badge_id for sb in student_badges]
    badge_map: dict[int, Badge] = {
        b.id: b
        for b in db.query(Badge).filter(Badge.id.in_(badge_ids)).all()
    }

    result: list[StudentBadgeOut] = []
    for sb in student_badges:
        badge = badge_map.get(sb.badge_id)
        if badge is None:
            continue  # orphan row — skip gracefully
        result.append(
            StudentBadgeOut(
                badge_id=badge.id,
                name=badge.name,
                description=badge.description,
                image_url=badge.image_url,
                awarded_at=sb.awarded_at,
            )
        )

    return StudentBadgesListOut(total_count=len(result), badges=result)
