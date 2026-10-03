from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

# ---------- 注册 ----------
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    # 1. 用户名是否已存在
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被占用",
        )

    # 2. 邮箱是否已存在
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )

    # 3. 创建用户（密码必须哈希，绝不存明文）
    user = User(
        username=payload.username,
        email=payload.email,
        password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

# ---------- 登录 ----------
@router.post(
    "/login",
    response_model=Token,
    summary="用户登录，返回 JWT",
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    # 1. 支持用用户名 或 邮箱 登录
    user = (
        db.query(User)
        .filter(
            (User.username == payload.username)
            | (User.email == payload.username)
        )
        .first()
    )

    # 2. 用户不存在，或密码错误 → 统一返回「账号或密码错误」
    #    （不要区分「用户不存在」和「密码错」，防止枚举攻击）
    if user is None or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 3. 签发 token，sub 放用户 ID
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return Token(access_token=access_token)

# ---------- 当前用户 ----------
@router.get(
    "/me",
    response_model=UserOut,
    summary="获取当前登录用户信息",
)
def me(current_user: User = Depends(get_current_user)):
    return current_user