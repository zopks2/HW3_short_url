from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True, nullable=False)
    custom_alias = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_accessed = Column(TIMESTAMP(timezone=True), nullable=True)
    access_count = Column(Integer, default=0)

    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
