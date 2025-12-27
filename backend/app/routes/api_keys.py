"""API Key管理API端点"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import logging

from ..core.auth import require_admin, generate_api_key, hash_api_key, get_api_key_prefix
from ..database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


class CreateAPIKeyRequest(BaseModel):
    """创建API Key请求"""
    name: str
    email: Optional[EmailStr] = None


class CreateAPIKeyResponse(BaseModel):
    """创建API Key响应"""
    id: int
    api_key: str  # 只在创建时返回完整Key
    key_prefix: str
    name: str
    email: Optional[str] = None
    is_active: bool = True


class UpdateAPIKeyRequest(BaseModel):
    """更新API Key请求"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    """API Key响应（不包含完整Key）"""
    id: int
    key_prefix: str
    name: str
    email: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_used_at: Optional[str] = None
    user_id: Optional[int] = None


class APIKeyListResponse(BaseModel):
    """API Key列表响应（包含分页信息）"""
    data: List[APIKeyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=APIKeyListResponse)
async def get_api_keys(
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    name_filter: Optional[str] = Query(None, description="Filter by name (partial match)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: dict = Depends(require_admin())
):
    """获取所有API Key列表（需要管理员权限）"""
    db = get_database()
    api_keys = await db.get_api_keys(
        limit=limit,
        offset=offset,
        name_filter=name_filter,
        is_active=is_active
    )
    
    # 获取总数（用于分页）
    total_count = await db.get_api_keys_count(
        name_filter=name_filter,
        is_active=is_active
    )
    
    result = [
        APIKeyResponse(
            id=key["id"],
            key_prefix=key["key_prefix"],
            name=key["name"],
            email=key.get("email"),
            is_active=bool(key.get("is_active", True)),
            created_at=key.get("created_at"),
            updated_at=key.get("updated_at"),
            last_used_at=key.get("last_used_at"),
            user_id=key.get("user_id")
        )
        for key in api_keys
    ]
    
    return APIKeyListResponse(
        data=result,
        total=total_count,
        page=(offset // limit) + 1 if limit > 0 else 1,
        page_size=limit,
        total_pages=(total_count + limit - 1) // limit if limit > 0 else 1
    )


@router.get("/{api_key_id}", response_model=APIKeyResponse)
async def get_api_key(
    api_key_id: int,
    current_user: dict = Depends(require_admin())
):
    """获取指定API Key详情（需要管理员权限）"""
    db = get_database()

    # 直接通过ID查询
    api_key = await db.get_api_key_encrypted(api_key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return APIKeyResponse(
        id=api_key["id"],
        key_prefix=api_key["key_prefix"],
        name=api_key["name"],
        email=api_key.get("email"),
        is_active=bool(api_key.get("is_active", True)),
        created_at=api_key.get("created_at"),
        updated_at=api_key.get("updated_at"),
        last_used_at=api_key.get("last_used_at"),
        user_id=api_key.get("user_id")
    )


@router.post("", response_model=CreateAPIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: dict = Depends(require_admin())
):
    """创建新API Key（需要管理员权限）"""
    db = get_database()

    # 生成新的API Key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_prefix = get_api_key_prefix(api_key)

    # 加密完整 API Key
    try:
        encrypted_key = db.fernet.encrypt(api_key.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="加密 API Key 失败"
        )

    # 创建API Key
    api_key_id = await db.create_api_key(
        key_hash=key_hash,
        key_prefix=key_prefix,
        encrypted_key=encrypted_key,
        name=request.name,
        email=request.email.lower() if request.email else None,
        user_id=current_user.get("user_id")
    )

    if not api_key_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )

    return CreateAPIKeyResponse(
        id=api_key_id,
        api_key=api_key,  # 只在创建时返回完整Key
        key_prefix=key_prefix,
        name=request.name,
        email=request.email,
        is_active=True
    )


@router.put("/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: int,
    request: UpdateAPIKeyRequest,
    current_user: dict = Depends(require_admin())
):
    """更新API Key（需要管理员权限）"""
    db = get_database()

    # 检查API Key是否存在
    api_key = await db.get_api_key_encrypted(api_key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # 更新API Key
    success = await db.update_api_key(
        api_key_id=api_key_id,
        name=request.name,
        email=request.email.lower() if request.email else None,
        is_active=request.is_active
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key"
        )

    # 获取更新后的API Key
    updated_key = await db.get_api_key_encrypted(api_key_id)

    return APIKeyResponse(
        id=updated_key["id"],
        key_prefix=updated_key["key_prefix"],
        name=updated_key["name"],
        email=updated_key.get("email"),
        is_active=bool(updated_key.get("is_active", True)),
        created_at=updated_key.get("created_at"),
        updated_at=updated_key.get("updated_at"),
        last_used_at=updated_key.get("last_used_at"),
        user_id=updated_key.get("user_id")
    )


@router.delete("/{api_key_id}")
async def delete_api_key(
    api_key_id: int,
    current_user: dict = Depends(require_admin())
):
    """删除API Key（需要管理员权限）"""
    db = get_database()

    # 检查API Key是否存在
    api_key = await db.get_api_key_encrypted(api_key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # 删除API Key
    success = await db.delete_api_key(api_key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )

    return {"message": "API key deleted successfully"}


@router.get("/{api_key_id}/full", response_model=dict)
async def get_full_api_key(
    api_key_id: int,
    current_user: dict = Depends(require_admin())
):
    """获取完整API Key（需要管理员权限，仅在需要时调用）"""
    from ..database import get_database

    db = get_database()

    # 获取包含加密 key 的 API Key 信息
    api_key = await db.get_api_key_encrypted(api_key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # 检查是否存储了加密的完整 key
    encrypted_key = api_key.get('encrypted_key')
    if not encrypted_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="完整 API Key 不可用（可能是在更新前创建的）。如需要完整 Key，请删除后重新创建。"
        )

    try:
        # 解密 API Key
        decrypted_key = db.fernet.decrypt(encrypted_key.encode()).decode()
        return {
            "id": api_key_id,
            "api_key": decrypted_key,
            "key_prefix": api_key["key_prefix"]
        }
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="解密 API Key 失败"
        )
