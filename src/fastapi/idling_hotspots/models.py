from sqlalchemy import Column, Date, Float, Integer, String

from src.fastapi.database.database import Base


class IdlingHotspotModel(Base):
    __tablename__ = "idling_hotspots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    idle_duration_minutes = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
