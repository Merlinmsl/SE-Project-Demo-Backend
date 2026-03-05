from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    province_id = Column(Integer, ForeignKey("provinces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    province = relationship("Province", lazy="joined")

    __table_args__ = (
        UniqueConstraint("province_id", "name", name="uq_district_province_name"),
    )
