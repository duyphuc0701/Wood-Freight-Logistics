from datetime import UTC, datetime

from sqlalchemy import TIMESTAMP, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.fastapi.database.database import Base


class FaultEventModel(Base):
    __tablename__ = "fault_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.now(UTC)
    )
    fault_payload: Mapped[str] = mapped_column(String(100), nullable=False)
    fault_code: Mapped[str] = mapped_column(String(100), nullable=False)
    fault_label: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self):
        return (
            f"<FaultEvent(device_id='{self.device_id}', "
            f"timestamp='{self.timestamp}', "
            f"fault_code='{self.fault_code}', "
            f"fault_label='{self.fault_label}')>"
        )
