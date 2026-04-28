"""Eagerly import every model so SQLAlchemy can resolve string-based
relationship() references (e.g. Student → "District") no matter which
model the caller imports first.
"""

from .province import Province
from .district import District
from .daily_streak import DailyStreak
from .daily_completion import DailyCompletion
from .notification import Notification
from .ai_chat_log import AiChatLog
from .student import Student
from .subject import Subject
from .topic import Topic
from .grade import Grade
from .resource import Resource
from .question import Question
from .quiz_attempt import QuizAttempt
from .quiz_session import QuizSession
from .quiz_answer import QuizAnswer
from .leaderboard import Leaderboard
from .student_stats import StudentSubjectStats, StudentTopicStats
from .badge import Badge, StudentBadge
from .study_streak import StudyStreak
from .admin import Admin  # noqa: F401
