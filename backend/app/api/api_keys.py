"""API Key管理API端点"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from ..auth import require_admin, generate_api_key, hash_api_key, get_api_key_prefix
from ..database import get_database

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
    
    # 获取API Key列表并查找指定ID
    api_keys = await db.get_api_keys(limit=1000, offset=0)
    api_key = next((k for k in api_keys if k["id"] == api_key_id), None)
    
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
    
    # 创建API Key
    api_key_id = await db.create_api_key(
        key_hash=key_hash,
        key_prefix=key_prefix,
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
    api_keys = await db.get_api_keys(limit=1000, offset=0)
    api_key = next((k for k in api_keys if k["id"] == api_key_id), None)
    
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
    api_keys = await db.get_api_keys(limit=1000, offset=0)
    updated_key = next((k for k in api_keys if k["id"] == api_key_id), None)
    
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
    api_keys = await db.get_api_keys(limit=1000, offset=0)
    api_key = next((k for k in api_keys if k["id"] == api_key_id), None)
    
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
