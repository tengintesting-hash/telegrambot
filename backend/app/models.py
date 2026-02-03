from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import BigInteger


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    referrer = relationship("User", remote_side=[id])


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    referred_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    reward_paid: Mapped[bool] = mapped_column(Boolean, default=False)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    reward: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserTask(Base):
    __tablename__ = "user_tasks"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.id"), primary_key=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
