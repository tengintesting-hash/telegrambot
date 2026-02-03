import asyncio
from datetime import datetime
from decimal import Decimal
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import BigInteger

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://app:app@mysql:3306/app")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")
ADMIN_IDS = {int(item) for item in os.getenv("ADMIN_IDS", "").split(",") if item.strip()}


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


engine: AsyncEngine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


dp = Dispatcher()


async def get_or_create_user(session: AsyncSession, message: Message) -> User:
    user = await session.get(User, message.from_user.id)
    if not user:
        role = "admin" if message.from_user.id in ADMIN_IDS else "user"
        user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            role=role,
            registered_at=datetime.utcnow(),
        )
        session.add(user)
        await session.commit()
    return user


async def handle_referral(session: AsyncSession, user: User, start_param: str | None) -> None:
    if not start_param or not start_param.startswith("ref_"):
        return
    try:
        referrer_id = int(start_param.split("ref_")[-1])
    except ValueError:
        return
    if referrer_id == user.id:
        return
    referrer = await session.get(User, referrer_id)
    if not referrer:
        return
    if user.referrer_id:
        return
    user.referrer_id = referrer_id
    session.add(Referral(referrer_id=referrer_id, referred_id=user.id, reward_paid=False))
    await session.commit()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
    return member.status in {"member", "administrator", "creator"}


@dp.message(Command("start"))
async def start(message: Message, bot: Bot) -> None:
    if not await check_subscription(bot, message.from_user.id):
        await message.answer("Please join our channel to use this bot.")
        return
    start_param = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message)
        await handle_referral(session, user, start_param)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Open WebApp", url=WEBAPP_URL)]]
    )
    await message.answer("Welcome! Use the WebApp to manage your account.", reply_markup=keyboard)


@dp.message(Command("profile"))
async def profile(message: Message) -> None:
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message)
        await session.refresh(user)
        await message.answer(
            f"User: @{user.username or 'anonymous'}\nBalance: {user.balance}\nRole: {user.role}"
        )


@dp.message(Command("tasks"))
async def tasks(message: Message) -> None:
    async with SessionLocal() as session:
        tasks = (await session.execute(select(Task).where(Task.is_active.is_(True)))).scalars().all()
        if not tasks:
            await message.answer("No active tasks.")
            return
        lines = [f"{task.title} — {task.reward}" for task in tasks]
        await message.answer("Active tasks:\n" + "\n".join(lines))


@dp.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Admin only.")
        return
    await message.answer("Open the WebApp to manage users.")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
