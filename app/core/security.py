from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
)

# =========================
# 2. 密码加密配置
# =========================
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

# =========================
# 3. 密码相关函数
# =========================
def hash_password(password: str) -> str:
    """将明文密码进行哈希加密"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码和数据库中的密码哈希是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)

# =========================
# 4. 创建 JWT
# =========================
def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt

# =========================
# 5. 解码 JWT
# =========================
def decode_access_token(token: str) -> dict | None:
    """
    解码 JWT Token

    Token 正确：返回 payload
    Token 错误：返回 None
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError:
        return None