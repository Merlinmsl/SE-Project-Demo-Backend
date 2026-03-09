from sqlalchemy import Column, BigInteger, String, DateTime
from datetime import datetime, timezone
from app.db.base import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    display_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
