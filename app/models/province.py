from sqlalchemy import Column, Integer, String
from app.db.base import Base


class Province(Base):
    __tablename__ = "provinces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
