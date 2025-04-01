from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from typing import Optional, List
from pydantic import HttpUrl
import redis.asyncio as redis

from auth.database import get_async_session, User
from auth.auth import fastapi_users
from . import crud
from . import schemas
from redis_client import get_redis_connection

router = APIRouter(
    prefix="/links",
    tags=["Links"]
)

get_optional_current_user = fastapi_users.current_user(active=True, optional=True)

get_current_active_user = fastapi_users.current_user(active=True)

@router.post(
    "/shorten",
    response_model=schemas.LinkRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать короткую ссылку",
    description="Создает новую короткую ссылку для указанного URL. Доступно всем пользователям."
)
async def create_short_link(
    link_in: schemas.LinkCreate,
    db: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Создает новую короткую ссылку.

    - **original_url**: Оригинальный URL для сокращения (обязательно).
    - **custom_alias**: Желаемый короткий код (опционально, должен быть уникальным).
    - **expires_at**: Дата и время истечения срока действия (опционально).
    - **Требуется аутентификация**: Нет (но если пользователь аутентифицирован, ссылка будет привязана к нему).
    """
    try:
        created_link = await crud.create_link(db=db, link_data=link_in, user=user)
        return created_link
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error creating link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать ссылку из-за внутренней ошибки."
        )

@router.get(
    "/search",
    response_model=List[schemas.LinkRead], # Возвращаем список ссылок
    summary="Поиск ссылок по оригинальному URL",
    description="Находит все короткие ссылки текущего пользователя для указанного оригинального URL."
)
async def search_links_by_original_url(
    # Используем Query для параметра запроса, делаем его обязательным
    original_url: HttpUrl = Query(..., description="Оригинальный URL для поиска"),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user) # Требуем аутентификацию
):
    """
    Ищет и возвращает все короткие ссылки, созданные текущим
    аутентифицированным пользователем для заданного `original_url`.
    """
    # Передаем строку в CRUD функцию
    links = await crud.get_links_by_original_url_for_user(
        db=db, original_url=str(original_url), user=user
    )
    return links

@router.get(
    "/{short_code}/stats",
    response_model=schemas.LinkStats,
    summary="Получить статистику по ссылке",
    description="Возвращает статистику использования для указанной короткой ссылки (или алиаса)."
)
async def get_link_stats(
    short_code: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Возвращает статистику для ссылки:
    - оригинальный URL
    - дата создания
    - дата последнего доступа
    - количество переходов
    
    Доступно всем пользователям.
    """
    link = await crud.get_any_link_by_code_or_alias(db, short_code)
    
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ссылка не найдена."
        )
        
    return link

@router.put(
    "/{short_code}",
    response_model=schemas.LinkRead,
    summary="Обновить оригинальный URL ссылки",
    description="Обновляет оригинальный URL для существующей короткой ссылки, если она принадлежит текущему пользователю."
)
async def update_link(
    short_code: str,
    link_update_data: schemas.LinkUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
    redis_conn: redis.Redis = Depends(get_redis_connection)
):
    """
    Обновляет оригинальный URL существующей короткой ссылки.
    Инвалидирует кэш Redis для этой ссылки.
    """
    link_to_update = await crud.get_link_by_short_code_for_user(
        db=db, short_code=short_code, user=user
    )

    if link_to_update is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ссылка не найдена или у вас нет прав на ее изменение."
        )
    
    # --- Инвалидация кэша --- 
    redis_key = f"redirect:{link_to_update.short_code}"
    await redis_conn.delete(redis_key)
    alias_redis_key = None
    if link_to_update.custom_alias:
        alias_redis_key = f"redirect:{link_to_update.custom_alias}"
        await redis_conn.delete(alias_redis_key)
    print(f"Invalidated Redis cache for keys: {redis_key}, {alias_redis_key if alias_redis_key else ''}")
    # -------------------------
    
    updated_link = await crud.update_link_original_url(
        db=db, 
        link_to_update=link_to_update, 
        new_original_url=str(link_update_data.original_url)
    )
    
    return updated_link

@router.delete(
    "/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить короткую ссылку",
    description="Удаляет короткую ссылку, если она принадлежит текущему пользователю.",
)
async def delete_short_link(
    short_code: str,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
    redis_conn: redis.Redis = Depends(get_redis_connection)
):
    """
    Удаляет связь короткой ссылки с оригинальным URL.
    Инвалидирует кэш Redis для этой ссылки.
    """
    link_to_delete = await crud.get_link_by_short_code_for_user(
        db=db, short_code=short_code, user=user
    )

    if link_to_delete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ссылка не найдена или у вас нет прав на ее удаление."
        )

    # --- Инвалидация кэша (перед удалением из БД) --- 
    redis_key = f"redirect:{link_to_delete.short_code}"
    await redis_conn.delete(redis_key)
    alias_redis_key = None
    if link_to_delete.custom_alias:
        alias_redis_key = f"redirect:{link_to_delete.custom_alias}"
        await redis_conn.delete(alias_redis_key)
    print(f"Invalidated Redis cache for keys: {redis_key}, {alias_redis_key if alias_redis_key else ''}")
    # ------------------------------------------------

    await crud.delete_link(db=db, link_to_delete=link_to_delete)
    return None