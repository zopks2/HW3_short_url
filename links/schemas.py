from pydantic import BaseModel, HttpUrl, Field, ConfigDict
import datetime
import uuid
from typing import Optional

class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=30,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Опциональный уникальный алиас для ссылки (3-30 символов, буквы, цифры, _, -)"
    )

    expires_at: Optional[datetime.datetime] = Field(
        default=None,
        description="Опциональная дата и время истечения срока действия ссылки (UTC)"
    )

class LinkRead(BaseModel):
    original_url: HttpUrl
    short_code: str
    custom_alias: Optional[str] = None
    created_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)

class LinkStats(BaseModel):
    original_url: HttpUrl
    created_at: datetime.datetime
    last_accessed: Optional[datetime.datetime] = None
    access_count: int

    model_config = ConfigDict(from_attributes=True)

class LinkUpdate(BaseModel):
    original_url: HttpUrl