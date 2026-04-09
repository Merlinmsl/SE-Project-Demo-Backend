from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime, timezone
from app.db.base import Base


class Badge(Base):
    """Represents an achievement badge that can be awarded to students.

    The ``image_url`` column holds a publicly accessible URL for the badge
    artwork (e.g. a Supabase Storage URL).  It is nullable so that existing
    badges created before this column was added continue to load without error.
    """

    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    # URL to the badge artwork stored in Supabase Storage (or any CDN).
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class StudentBadge(Base):
    """Join table recording which badges have been awarded to which students.

    The unique constraint on (student_id, badge_id) ensures a badge is only
    awarded once per student, making the award operation idempotent.
    """

    __tablename__ = "student_badges"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False)
    awarded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("student_id", "badge_id", name="uq_student_badge"),
    )
