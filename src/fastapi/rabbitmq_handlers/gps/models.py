from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.fastapi.database.database import Base


class GPSEventModel(Base):
    __tablename__ = "gps_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    speed: Mapped[float] = mapped_column(Float, nullable=False)
    odometer: Mapped[float] = mapped_column(Float, nullable=False)
    power_on: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_gauge: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )
