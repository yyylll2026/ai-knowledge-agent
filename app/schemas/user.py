from datetime import datetime
from pydantic import BaseModel,EmailStr, Field

class UserCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名"
    )
    email:EmailStr = Field(...,description="邮箱")
    password: str = Field(
        ...,
        min_length=6,
        max_length=64,
        description="密码，至少 6 位",
    )
class UserLogin(BaseModel):
    """登录请求体（JSON 方式，方便前后端联调）"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")
class UserOut(BaseModel):
    """返回给前端的用户信息（不含密码）"""
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
class Token(BaseModel):
    """登录成功后返回的 token"""
    access_token: str
    token_type: str = "bearer"