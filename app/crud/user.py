import random
import string
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class CRUDUser:
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, user_in: UserCreate) -> User:

        existing_user = await self.get_by_email(db, user_in.email)
        if existing_user:
            raise ValueError("Email already registered")

        verification_code = ''.join(random.choices(string.digits, k=6))

        user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            hashed_password=get_password_hash(user_in.password),
            verification_code=verification_code,
            is_verified=False
        )
        db.add(user)
        await db.flush()
        return user

    async def verify(self, db: AsyncSession, email: str, code: str) -> bool:
        user = await self.get_by_email(db, email)
        if not user or user.verification_code != code:
            return False

        user.is_verified = True
        user.verification_code = None
        await db.commit()
        return True

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        user = await self.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user


user_crud = CRUDUser()
