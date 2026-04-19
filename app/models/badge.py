from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime, timezone
from app.db.base import Base


class Badge(Base):
    """Represents a badge type that can be awarded to students.

    Columns
    -------
    image_url : URL of the badge image asset stored in Supabase Storage.
    category  : Logical grouping, e.g. 'district', 'streak', 'quiz'.
    """

    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)          # badge logo URL (Supabase Storage)
    category = Column(String(100), nullable=True)    # e.g. 'district', 'streak', 'quiz'
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
