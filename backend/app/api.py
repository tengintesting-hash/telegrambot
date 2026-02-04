import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, init_redis, parse_admin_ids
from app.models import Referral, Task, User, UserTask
from app.tg_auth import validate_init_data
from app.ws import manager

router = APIRouter()


class AuthPayload(BaseModel):
    initData: str


class BanPayload(BaseModel):
    is_banned: bool


class UserOut(BaseModel):
    id: int
    username: str | None
    balance: Decimal
    referrer_id: int | None
    role: str
    registered_at: datetime
    is_banned: bool


async def rate_limit(request: Request) -> None:
    redis = await init_redis()
    key = f"rl:{request.client.host}:{request.url.path}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)
    if current > 60:
        raise HTTPException(status_code=429, detail="Too many requests")


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> User:
    data = validate_init_data(x_telegram_init_data or "")
    user_data = json.loads(data["user"])
    user_id = int(user_data["id"])
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=403, detail="User not registered")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")
    return user


async def ensure_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
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
    user.referrer_id = referrer_id
    session.add(Referral(referrer_id=referrer_id, referred_id=user.id, reward_paid=False))
    await session.commit()


@router.post("/auth/telegram", dependencies=[Depends(rate_limit)])
async def auth_telegram(payload: AuthPayload, session: AsyncSession = Depends(get_session)) -> UserOut:
    data = validate_init_data(payload.initData)
    user_data = json.loads(data["user"])
    user_id = int(user_data["id"])
    username = user_data.get("username")
    user = await session.get(User, user_id)
    if not user:
        role = "admin" if user_id in parse_admin_ids() else "user"
        user = User(id=user_id, username=username, role=role, registered_at=datetime.utcnow())
        session.add(user)
        await session.commit()
        await handle_referral(session, user, data.get("start_param"))
    else:
        if user.is_banned:
            raise HTTPException(status_code=403, detail="User is banned")
        if username and user.username != username:
            user.username = username
            await session.commit()
    return UserOut.model_validate(user)


@router.get("/me", dependencies=[Depends(rate_limit)])
async def get_me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/tasks", dependencies=[Depends(rate_limit)])
async def list_tasks(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    tasks = (await session.execute(select(Task).where(Task.is_active.is_(True)))).scalars().all()
    completed = (
        await session.execute(select(UserTask.task_id).where(UserTask.user_id == user.id))
    ).scalars().all()
    completed_set = set(completed)
    return [
        {
            "id": task.id,
            "title": task.title,
            "reward": str(task.reward),
            "completed": task.id in completed_set,
        }
        for task in tasks
    ]


@router.post("/tasks/{task_id}/complete", dependencies=[Depends(rate_limit)])
async def complete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    task = await session.get(Task, task_id)
    if not task or not task.is_active:
        raise HTTPException(status_code=404, detail="Task not found")
    existing = await session.get(UserTask, {"user_id": user.id, "task_id": task_id})
    if existing and existing.completed:
        return {"status": "already_completed"}
    if not existing:
        existing = UserTask(user_id=user.id, task_id=task_id, completed=True)
        session.add(existing)
    else:
        existing.completed = True
    user.balance = (user.balance or Decimal("0.00")) + task.reward
    await session.commit()
    await manager.send_balance(user.id, str(user.balance))
    return {"status": "completed", "balance": str(user.balance)}


@router.get("/referrals", dependencies=[Depends(rate_limit)])
async def list_referrals(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = (
        await session.execute(select(Referral).where(Referral.referrer_id == user.id))
    ).scalars().all()
    return [
        {
            "id": row.id,
            "referred_id": row.referred_id,
            "reward_paid": row.reward_paid,
        }
        for row in rows
    ]


@router.get("/admin/users", dependencies=[Depends(rate_limit)])
async def admin_users(
    _: User = Depends(ensure_admin),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    users = (await session.execute(select(User))).scalars().all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "balance": str(user.balance),
            "role": user.role,
            "is_banned": user.is_banned,
        }
        for user in users
    ]


@router.post("/admin/user/{user_id}/ban", dependencies=[Depends(rate_limit)])
async def ban_user(
    user_id: int,
    payload: BanPayload,
    _: User = Depends(ensure_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(User).where(User.id == user_id))
    target = result.scalars().first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_banned = payload.is_banned
    await session.commit()
    return {"id": target.id, "is_banned": target.is_banned}
