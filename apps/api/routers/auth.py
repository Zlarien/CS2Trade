import os

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from auth.openid import OpenIDVerificationError, build_login_url, verify_openid_callback
from auth.session import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    create_session,
    destroy_session,
)
from db.models import User
from dependencies import get_db_session, get_http_client, get_redis_client

router = APIRouter(prefix="/auth/steam", tags=["auth"])


def _app_base_url() -> str:
    return os.environ.get("APP_BASE_URL", "http://localhost:8000")


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000")


def _cookie_secure() -> bool:
    return os.environ.get("COOKIE_SECURE", "true").lower() != "false"


@router.get("/login")
async def login() -> RedirectResponse:
    base = _app_base_url()
    url = build_login_url(return_to=f"{base}/auth/steam/callback", realm=base)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    request: Request,
    http_client: httpx.AsyncClient = Depends(get_http_client),
    redis_client: Redis = Depends(get_redis_client),
    db_session: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    params = dict(request.query_params)
    try:
        steamid64 = await verify_openid_callback(params, http_client)
    except OpenIDVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = await db_session.get(User, steamid64)
    if user is None:
        db_session.add(User(steamid64=steamid64))
        await db_session.commit()

    session_id = await create_session(steamid64, redis_client)

    redirect = RedirectResponse(url=_frontend_url())
    redirect.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
    )
    return redirect


@router.post("/logout")
async def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    redis_client: Redis = Depends(get_redis_client),
) -> dict:
    if session_id is not None:
        await destroy_session(session_id, redis_client)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"status": "ok"}
