from enum import Enum

from sqlalchemy import Column, Integer, DateTime, String, Enum as SQLEnum, Boolean
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

class Base(AsyncAttrs, DeclarativeBase):
    pass


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_verified = Column(Boolean, default=False)  # True = verified, False = unverified
    verification_code = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Note: created_at is used for automatic cleanup logic (unverified users after 2 days)
