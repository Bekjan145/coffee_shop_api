from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_active_admin, get_user_updater_permission
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate
from typing import List

router = APIRouter()


@router.get("/me", summary="Get current user", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", summary="Get all users (Admin only)")
async def read_users(
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_admin)
) -> List[UserOut]:
    """Get all users (Admin only)"""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return users


@router.get("/users/{user_id}", summary="Get user by ID (Admin only)", response_model=UserOut)
async def read_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_admin)
):
    """Get user by ID (Admin only)"""
    user = await user_crud.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}", summary="Update user (Self or Admin)")
async def update_user(
        user_id: int,
        user_update: UserUpdate,
        db: AsyncSession = Depends(get_db),
        updater: User = Depends(get_user_updater_permission)
) -> UserOut:
    """
    Update user logic:
    - Self: full_name only
    - Admin: full_name + role
    """
    target_user = await user_crud.get_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)

    if target_user.id == updater.id:
        if "role" in update_data:
            raise HTTPException(
                status_code=403,
                detail="Cannot change own role"
            )
        if "full_name" in update_data:
            target_user.full_name = update_data["full_name"]
    else:
        for field, value in update_data.items():
            setattr(target_user, field, value)

    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.delete("/users/{user_id}", summary="Delete user (Admin only)")
async def delete_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_admin)
):
    """Delete user (Admin only)"""
    user = await user_crud.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"message": "User deleted successfully"}
