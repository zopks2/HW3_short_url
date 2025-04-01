import uvicorn
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from redis_client import get_redis_connection, close_redis_pool, get_redis_pool

from auth.database import User, get_async_session
from auth.schemas import UserCreate, UserRead
from auth.auth import auth_backend, fastapi_users
from links.router import router as links_router
from links import crud as links_crud

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup: Initializing resources...")
    _ = get_redis_pool() 
    yield
    print("Application shutdown: Cleaning up resources...")
    await close_redis_pool()

app = FastAPI(
    title="URL Shortener API",
    description="Сервис для сокращения URL и управления ссылками.",
    version="0.1.0",
    lifespan=lifespan
)

REDIS_REDIRECT_KEY_PREFIX = "redirect:"
REDIS_REDIRECT_TTL = 3600 

@app.get(
    "/{short_code}", 
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    tags=["Redirect"],
    summary="Перенаправление по короткой ссылке (с кэшированием)",
    description="Находит оригинальный URL по короткому коду или алиасу (сначала в Redis, потом в БД) и перенаправляет пользователя."
)
async def redirect_to_original_url(
    short_code: str,
    db: AsyncSession = Depends(get_async_session),
    redis_conn: redis.Redis = Depends(get_redis_connection) 
):
    redis_key = f"{REDIS_REDIRECT_KEY_PREFIX}{short_code}"
    cached_url = await redis_conn.get(redis_key)
    original_url: str | None = None
    link_from_db: links_crud.Link | None = None 

    if cached_url:
        print(f"Cache hit for {short_code}")
        original_url = cached_url
        link_from_db = await links_crud.get_any_link_by_code_or_alias(db, short_code)
        if link_from_db:
             await links_crud.update_link_stats(db, link_from_db)
             await db.commit()
        else:
             await redis_conn.delete(redis_key)
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена.")
    else:
        print(f"Cache miss for {short_code}")
        link_from_db = await links_crud.get_active_link_by_code_or_alias(db, short_code)
        if link_from_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Ссылка не найдена или срок ее действия истек."
            )
        original_url = str(link_from_db.original_url)
        await redis_conn.set(redis_key, original_url, ex=REDIS_REDIRECT_TTL)
        print(f"Cached {short_code} -> {original_url} for {REDIS_REDIRECT_TTL}s")
        await links_crud.update_link_stats(db, link_from_db)
        await db.commit()

    return RedirectResponse(url=original_url)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["Auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(links_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", log_level="info", reload=False)