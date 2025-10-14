from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.base import Base

class Driver(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
