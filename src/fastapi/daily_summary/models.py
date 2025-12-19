from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from src.fastapi.database.database import Base


class DailyVehicleSummaryModel(Base):
    __tablename__ = "daily_vehicle_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(String(50), index=True, nullable=False)
    summary_date = Column(Date, nullable=False, index=True)
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)
    end_latitude = Column(Float, nullable=True)
    end_longitude = Column(Float, nullable=True)
    total_distance_km = Column(Float, nullable=False)
    total_operational_hours = Column(Float, nullable=False)
    trip_count = Column(Integer, nullable=False)
    fuel_consumed_liters = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("vehicle_id", "summary_date", name="uq_vehicle_summary"),
        {"sqlite_autoincrement": True},
    )
