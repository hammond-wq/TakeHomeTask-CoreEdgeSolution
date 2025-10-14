from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.infrastructure.db.base import Base

class CallLog(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent.id"), index=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("driver.id"), index=True, nullable=True)
    load_number: Mapped[str] = mapped_column(String(64), index=True)
    call_start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    call_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    call_outcome: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    provider_call_id: Mapped[str | None] = mapped_column(String(128), index=True)
    structured_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

Index("ix_calllog_outcome_start", CallLog.call_outcome, CallLog.call_start_time)
