from typing import AsyncGenerator
from datetime import datetime
import uuid

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, TIMESTAMP, ForeignKey, UUID
from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from models.models import Base

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Наследуемся от Base и SQLAlchemyBaseUserTableUUID для совместимости,
# но определяем все поля явно, чтобы помочь Alembic.
class User(SQLAlchemyBaseUserTableUUID, Base):
    # __tablename__ берется из SQLAlchemyBaseUserTableUUID

    # Явно определяем все столбцы, которые должны быть в таблице
    # Типы данных берем из документации fastapi-users
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String(length=320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Добавляем наше кастомное поле
    registered_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)


# class User(Base):
#     __tablename__ = "user"

#     id = Column(UUID, primary_key=True, index=True)
#     email = Column(String, nullable=False)
#     hashed_password = Column(String, nullable=False)
#     registered_at = Column(TIMESTAMP, default=datetime.utcnow)
#     is_active = Column(Boolean, default=True, nullable=False)
#     is_superuser = Column(Boolean, default=False, nullable=False)
#     is_verified = Column(Boolean, default=False, nullable=False)

#     links = relationship("Link", back_populates="user")

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# убираем
# async def create_db_and_tables():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

