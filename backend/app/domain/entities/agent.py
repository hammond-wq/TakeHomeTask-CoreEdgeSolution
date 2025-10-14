from sqlalchemy import String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.base import Base

class Agent(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    language: Mapped[str] = mapped_column(String(40), default="English")
    voice_type: Mapped[str] = mapped_column(String(40), default="Male")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
