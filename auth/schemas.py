import datetime
import uuid
from typing import Optional

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, ConfigDict


class UserRead(schemas.BaseUser[uuid.UUID]):
    username: str 
    registered_at: datetime.datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UserCreate(schemas.BaseUserCreate):
    username: str


class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = None




# class UserUpdate(schemas.BaseUserUpdate):
#     first_name: Optional[str]
#     birthdate: Optional[datetime.date]
