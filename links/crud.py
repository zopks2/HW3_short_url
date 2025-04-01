from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, exists, update, text
from sqlalchemy.orm import selectinload
import uuid
import datetime
import hashlib
import base64
import secrets
from typing import Optional

from models.models import Link
from auth.database import User
from . import schemas

async def generate_short_code(db: AsyncSession, original_url: str, length: int = 7) -> str:
    """Генерирует уникальный короткий код на основе хэша URL и соли (с рекурсией при коллизии)."""
    salt = secrets.token_urlsafe(8)
    data_to_hash = f"{original_url}{salt}"
    hasher = hashlib.sha256()
    hasher.update(data_to_hash.encode('utf-8'))
    encoded_hash = base64.urlsafe_b64encode(hasher.digest()).decode('utf-8').replace('=', '')
    
    # Берем префикс нужной длины
    short_code = encoded_hash[:length]
    
    # Проверяем уникальность префикса
    exists_query = select(exists().where(Link.short_code == short_code))
    code_exists = (await db.execute(exists_query)).scalar()
    
    if not code_exists:
        # Если код уникален, возвращаем его
        return short_code
    else:
        # Если код занят, вызываем функцию заново для генерации нового
        print(f"Collision detected for {short_code}, regenerating...") # Для отладки
        return await generate_short_code(db, original_url, length)

async def get_link_by_short_code_for_user(
    db: AsyncSession, short_code: str, user: User
) -> Link | None:
    statement = (
        select(Link)
        .where(Link.short_code == short_code)
        .where(Link.user_id == user.id)
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none()

async def get_link_by_alias(db: AsyncSession, alias: str) -> Link | None:
    statement = select(Link).where(Link.custom_alias == alias)
    result = await db.execute(statement)
    return result.scalar_one_or_none()

async def get_any_link_by_code_or_alias(db: AsyncSession, code: str) -> Link | None:
    statement = (
        select(Link)
        .where(
            (Link.short_code == code) | (Link.custom_alias == code)
        )
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none()

async def get_active_link_by_code_or_alias(db: AsyncSession, code: str) -> Link | None:
    now = datetime.datetime.now(datetime.timezone.utc)
    statement = (
        select(Link)
        .where(
            (Link.short_code == code) | (Link.custom_alias == code)
        )
        .where(
            (Link.expires_at == None) | (Link.expires_at > now)
        )
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none()

async def get_links_by_original_url_for_user(
    db: AsyncSession, original_url: str, user: User
) -> list[Link]:
    statement = (
        select(Link)
        .where(Link.original_url == original_url)
        .where(Link.user_id == user.id)
        .order_by(Link.created_at.desc())
    )
    result = await db.execute(statement)
    return list(result.scalars().all())

async def update_link_stats(db: AsyncSession, link: Link) -> None:
    link.access_count += 1
    link.last_accessed = datetime.datetime.now(datetime.timezone.utc)

async def update_link_original_url(
    db: AsyncSession, link_to_update: Link, new_original_url: str
) -> Link:
    link_to_update.original_url = new_original_url
    db.add(link_to_update)
    await db.commit()
    await db.refresh(link_to_update)
    return link_to_update

async def create_link(
    db: AsyncSession, 
    link_data: "schemas.LinkCreate",
    user: Optional[User] = None
) -> Link:
    original_url_str = str(link_data.original_url)
    if link_data.custom_alias:
        existing_alias = await get_link_by_alias(db, link_data.custom_alias)
        if existing_alias:
            raise ValueError("Этот алиас уже используется.")
        short_code = link_data.custom_alias
    else:
        short_code = await generate_short_code(db, original_url_str)
    
    db_link_data = {
        "original_url": original_url_str,
        "short_code": short_code,
        "custom_alias": link_data.custom_alias,
        "expires_at": link_data.expires_at,
        "user_id": user.id if user else None
    }
    
    db_link = Link(**db_link_data)
    db.add(db_link)
    await db.commit()
    await db.refresh(db_link)
    return db_link

async def delete_link(db: AsyncSession, link_to_delete: Link) -> None:
    await db.delete(link_to_delete)
    await db.commit()
