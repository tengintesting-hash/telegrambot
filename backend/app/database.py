import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator

from pydantic_settings import BaseSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from redis.asyncio import Redis

from app.models import Base, Task


class Settings(BaseSettings):
    database_url: str = "mysql+aiomysql://app:app@mysql:3306/app"
    redis_url: str = "redis://redis:6379/0"
    bot_token: str = ""
    admin_ids: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
redis_client: Redis | None = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


async def seed_tasks(session: AsyncSession) -> None:
    existing = await session.execute(select(Task))
    if existing.scalars().first():
        return
    session.add_all(
        [
            Task(title="Join community", reward=Decimal("1.00"), is_active=True),
            Task(title="Complete profile", reward=Decimal("2.50"), is_active=True),
        ]
    )
    await session.commit()


@asynccontextmanager
async def lifespan(_: object):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed_tasks(session)
    await init_redis()
    yield
    if redis_client is not None:
        await redis_client.close()
    await engine.dispose()


def parse_admin_ids() -> set[int]:
    ids = set()
    for raw in settings.admin_ids.split(","):
        raw = raw.strip()
        if raw:
            ids.add(int(raw))
    return ids


async def wait_for_db() -> None:
    for _ in range(30):
        try:
            async with engine.connect() as conn:
                await conn.execute(select(1))
            return
        except Exception:
            await asyncio.sleep(1)
    raise RuntimeError("Database not available")
