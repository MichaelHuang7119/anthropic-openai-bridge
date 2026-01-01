"""认证API端点"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
import json
import logging

from ..core.auth import (
    verify_password,
    hash_password,
    create_access_token,
    require_admin,
    require_user
)
from ..database import get_database
from ..core.permissions import DEFAULT_USER_PERMISSIONS, ADMIN_PERMISSIONS, PermissionCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    password: str
    name: Optional[str] = None


class RegisterResponse(BaseModel):
    """注册响应"""
    user_id: int
    email: str
    name: Optional[str] = None
    is_admin: bool = False


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    """修改密码响应"""
    success: bool
    message: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    db = get_database()
    
    # 获取用户
    user = await db.get_user_by_email(request.email.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # 验证密码
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # 检查用户是否激活
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # 更新最后登录时间
    await db.update_user_last_login(user["id"])
    
    # 创建访问令牌
    access_token = create_access_token(
        data={
            "sub": user["id"],
            "is_admin": user.get("is_admin", False)
        }
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "is_admin": user.get("is_admin", False)
        }
    )


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    current_user: dict = Depends(require_admin())
):
    """注册新用户（需要管理员权限）"""
    db = get_database()
    
    # 检查用户是否已存在
    existing_user = await db.get_user_by_email(request.email.lower())
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # 创建用户
    password_hash = hash_password(request.password)
    user_id = await db.create_user(
        email=request.email.lower(),
        password_hash=password_hash,
        name=request.name,
        is_admin=False  # 新用户默认不是管理员
    )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    return RegisterResponse(
        user_id=user_id,
        email=request.email.lower(),
        name=request.name,
        is_admin=False
    )


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(require_user())
):
    """获取当前用户信息（需要用户登录权限）"""
    db = get_database()

    # Get full user data including permissions
    user = await db.get_user_by_id(current_user["id"])

    # Parse permissions from database
    user_permissions = user.get("permissions") if user else None
    has_stored_permissions = False
    permissions = {}
    if user_permissions:
        try:
            perms = json.loads(user_permissions)
            # Only use stored permissions if not empty
            if perms and len(perms) > 0:
                has_stored_permissions = True
                # perms is a dict with string keys (already converted from JSON)
                # Ensure keys are lowercase for frontend compatibility
                permissions = {k.lower(): v for k, v in perms.items()}
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    if not has_stored_permissions:
        # No stored permissions, use defaults based on admin status (use lowercase for frontend)
        if user and user.get("is_admin"):
            permissions = {k.value.lower(): v for k, v in ADMIN_PERMISSIONS.items()}
        else:
            permissions = {k.value.lower(): v for k, v in DEFAULT_USER_PERMISSIONS.items()}

    # Return user info with permissions
    logger.debug(f"User permissions for {current_user['email']}: {permissions}")
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": user.get("name") if user else None,
        "is_admin": current_user.get("is_admin", False),
        "permissions": permissions
    }


@router.put("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(require_user())
):
    """修改密码"""
    db = get_database()

    # 验证当前密码
    user = await db.get_user_by_email(current_user["email"].lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 验证当前密码是否正确
    if not verify_password(request.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # 验证新密码强度
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )

    # 哈希新密码
    new_password_hash = hash_password(request.new_password)

    # 更新密码
    await db.update_user_password(user["id"], new_password_hash)

    return ChangePasswordResponse(
        success=True,
        message="Password changed successfully"
    )
