from sqlalchemy import (
    Column, BigInteger, Integer, Date, ForeignKey, Enum as SAEnum
)
from app.db.base import Base


class Leaderboard(Base):
    __tablename__ = "leaderboard"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    student_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True)
    mode = Column(
        SAEnum("alltime", "weekly", name="leaderboard_mode_enum"),
        nullable=False,
    )
    week_start = Column(Date, nullable=True)
    total_xp = Column(Integer, default=0)
