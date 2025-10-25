from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud.user import user_crud
from app.schemas.user import UserCreate, Token, LoginRequest
from app.core.security import create_access_token, create_refresh_token, verify_token
from datetime import timedelta
from app.core.config import settings

router = APIRouter()


@router.post("/signup", summary="Register new user", status_code=status.HTTP_201_CREATED)
async def signup(
        user_in: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with email and password.
    Returns tokens and verification code (printed to console in development).
    """
    user = await user_crud.create(db, user_in)
    await db.commit()

    # TODO: In production, send verification code via email/SMS
    print(f"🔑 Verification code for {user.email}: {user.verification_code}")

    return {
        "message": "User registered successfully. Check console for verification code.",
        "email": user.email
    }


@router.post("/login", summary="User login", response_model=Token)
async def login(
        user_in: LoginRequest,
        db: AsyncSession = Depends(get_db)
):
    """Login user and return access/refresh tokens"""
    user = await user_crud.authenticate(db, user_in.email, user_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": user.email})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", summary="Refresh access token")
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    payload = verify_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    email: str = payload.get("sub")
    access_token = create_access_token(data={"sub": email})

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/verify", summary="Verify user email")
async def verify_user(
        email: str,
        code: str,
        db: AsyncSession = Depends(get_db)
):
    """Verify user with verification code"""
    if await user_crud.verify(db, email, code):
        await db.commit()
        return {"message": "User verified successfully"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid verification code"
    )
