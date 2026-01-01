"""Permission management routes for admins."""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
import json
import logging

from ..core.auth import require_admin, require_users
from ..core.permissions import PermissionCategory, PERMISSIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/permissions", tags=["admin_permissions"])


class PermissionInfo(BaseModel):
    """Permission information for UI."""
    code: str
    name: str
    category: str
    description: str


class PermissionListResponse(BaseModel):
    """Response containing all available permissions."""
    permissions: list[PermissionInfo]
    categories: list[str]


class UserPermissionsUpdate(BaseModel):
    """Model for updating user permissions."""
    user_id: int
    permissions: dict[str, bool]


class UserPermissionsResponse(BaseModel):
    """User permissions response."""
    user_id: int
    permissions: dict[str, bool]


@router.get("", response_model=PermissionListResponse)
async def list_all_permissions(admin: dict = Depends(require_admin())):
    """List all available permissions (admin only). Excludes 'users' permission which is controlled by is_admin flag."""
    permissions_list = [
        PermissionInfo(
            code=code.value,
            name=data["name"],
            category=data["category"],
            description=data["description"]
        )
        for code, data in PERMISSIONS.items()
        if code != PermissionCategory.USERS  # Exclude users permission
    ]

    categories = list(set(p.category for p in permissions_list))

    return PermissionListResponse(
        permissions=permissions_list,
        categories=categories
    )


@router.get("/user/{user_id}", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: int,
    admin: dict = Depends(require_admin())
):
    """Get permissions for a specific user (admin only)."""
    from ..database import get_database
    from ..core.permissions import DEFAULT_USER_PERMISSIONS, ADMIN_PERMISSIONS

    db = get_database()
    user = await db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user permissions
    user_permissions = user.get("permissions")
    permissions = None

    if user_permissions:
        try:
            perms = json.loads(user_permissions)
            # Check if permissions dict is empty
            if perms and len(perms) > 0:
                permissions = dict(perms)
        except (json.JSONDecodeError, TypeError):
            pass

    # If no permissions stored or empty, initialize based on user role (use lowercase for frontend)
    if permissions is None:
        if user.get("is_admin"):
            permissions = {k.value.lower(): v for k, v in ADMIN_PERMISSIONS.items()}
            logger.info(f"Initialized admin permissions for user {user_id}")
        else:
            permissions = {k.value.lower(): v for k, v in DEFAULT_USER_PERMISSIONS.items()}
            logger.info(f"Initialized default permissions for user {user_id}")
        # Save the initialized permissions to database
        await db.update_user(user_id, permissions=json.dumps(permissions))

    return UserPermissionsResponse(
        user_id=user_id,
        permissions=permissions
    )


@router.put("/user/{user_id}")
async def update_user_permissions(
    user_id: int,
    update: UserPermissionsUpdate,
    admin: dict = Depends(require_admin())
):
    """Update permissions for a specific user (admin only)."""
    from ..database import get_database

    db = get_database()

    if user_id != update.user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch")

    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admins from removing their own admin status
    if user_id == admin["user_id"] and user.get("is_admin"):
        if "is_admin" in update.permissions and not update.permissions["is_admin"]:
            raise HTTPException(
                status_code=403,
                detail="Cannot remove admin status from yourself"
            )

    # Validate permission keys
    valid_codes = {p.value for p in PermissionCategory}
    invalid_keys = set(update.permissions.keys()) - valid_codes
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission keys: {invalid_keys}"
        )

    # Convert string keys to enum keys
    new_permissions = {
        PermissionCategory(k): v for k, v in update.permissions.items()
    }

    # Merge with existing permissions
    current_permissions = user.get("permissions")
    if current_permissions:
        try:
            merged = json.loads(current_permissions)
            # Permissions are already stored as strings
        except (json.JSONDecodeError, TypeError):
            merged = {}
    else:
        merged = {}

    # Apply updates - convert enum keys to lowercase strings for frontend compatibility
    merged.update({k.value.lower(): v for k, v in new_permissions.items()})

    # Save updated permissions
    await db.update_user(user_id, permissions=json.dumps(merged))

    logger.info(f"Admin {admin['email']} updated permissions for user {user_id}")

    return {
        "success": True,
        "message": "Permissions updated successfully",
        "permissions": merged
    }


@router.post("/user/{user_id}/reset")
async def reset_user_permissions(
    user_id: int,
    admin: dict = Depends(require_admin())
):
    """Reset user permissions to default (admin only)."""
    from ..database import get_database
    from ..core.permissions import DEFAULT_USER_PERMISSIONS, ADMIN_PERMISSIONS

    db = get_database()
    user = await db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Admins get all permissions, regular users get defaults
    if user.get("is_admin"):
        default_perms = ADMIN_PERMISSIONS
    else:
        default_perms = DEFAULT_USER_PERMISSIONS

    # Convert enum keys to lowercase strings for storage
    perms_to_save = {k.value.lower(): v for k, v in default_perms.items()}

    await db.update_user(user_id, permissions=json.dumps(perms_to_save))

    logger.info(f"Admin {admin['email']} reset permissions for user {user_id}")

    return {
        "success": True,
        "message": "Permissions reset to default",
        "permissions": perms_to_save
    }


class UserListItem(BaseModel):
    """User list item for admin view."""
    id: int
    email: str
    name: Optional[str] = None
    is_admin: bool
    is_active: bool
    created_at: str
    last_login_at: Optional[str] = None


class UserListResponse(BaseModel):
    """Response containing all users with pagination."""
    users: list[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class CreateUserRequest(BaseModel):
    """Request for creating a new user."""
    email: str
    password: str
    name: Optional[str] = None
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    """Request for updating user info."""
    email: Optional[str] = None
    name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    """Response for single user operations."""
    id: int
    email: str
    name: Optional[str] = None
    is_admin: bool
    is_active: bool
    created_at: str
    last_login_at: Optional[str] = None


@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: dict = Depends(require_users()),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size")
):
    """List all users with pagination (admin only)."""
    from ..database import get_database
    db = get_database()
    all_users = await db.get_all_users()

    total = len(all_users)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_users = all_users[start_idx:end_idx]

    users = []
    for user in paginated_users:
        users.append(UserListItem(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            is_admin=user.get("is_admin", False),
            is_active=user.get("is_active", True),
            created_at=user["created_at"],
            last_login_at=user.get("last_login_at")
        ))

    return UserListResponse(
        users=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/users/{user_id}", response_model=UserListItem)
async def get_user(
    user_id: int,
    admin: dict = Depends(require_users())
):
    """Get a specific user by ID (admin only)."""
    from ..database import get_database
    db = get_database()
    user = await db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserListItem(
        id=user["id"],
        email=user["email"],
        name=user.get("name"),
        is_admin=user.get("is_admin", False),
        is_active=user.get("is_active", True),
        created_at=user["created_at"],
        last_login_at=user.get("last_login_at")
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    request: CreateUserRequest,
    admin: dict = Depends(require_users())
):
    """Create user (admin only). Permissions are set automatically based on role."""
    from ..database import get_database
    from ..core.auth import hash_password
    import re

    db = get_database()

    # Validate email format
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, request.email.lower()):
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Check if email already exists
    existing = await db.get_user_by_email(request.email.lower())
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate password strength
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Create user - permissions are set automatically by create_user based on is_admin
    password_hash = hash_password(request.password)
    user_id = await db.create_user(
        email=request.email.lower(),
        password_hash=password_hash,
        name=request.name,
        is_admin=request.is_admin
    )

    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Get the created user
    new_user = await db.get_user_by_id(user_id)

    logger.info(f"Admin {admin['email']} created user: {request.email} (admin: {request.is_admin})")

    return UserResponse(
        id=new_user["id"],
        email=new_user["email"],
        name=new_user.get("name"),
        is_admin=new_user.get("is_admin", False),
        is_active=new_user.get("is_active", True),
        created_at=new_user["created_at"],
        last_login_at=new_user.get("last_login_at")
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    admin: dict = Depends(require_users())
):
    """Update user info (admin only)."""
    from ..database import get_database
    from ..core.permissions import DEFAULT_USER_PERMISSIONS, ADMIN_PERMISSIONS
    import re

    db = get_database()

    # Check if user exists
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from deactivating themselves
    if user_id == admin["user_id"]:
        if request.is_active is False:
            raise HTTPException(status_code=403, detail="Cannot deactivate your own account")

    # Prevent admin from removing their own admin status
    if user_id == admin["user_id"] and user.get("is_admin"):
        if request.is_admin is False:
            raise HTTPException(status_code=403, detail="Cannot remove your own admin status")

    # Validate email if provided
    if request.email:
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, request.email.lower()):
            raise HTTPException(status_code=400, detail="Invalid email format")

        # Check if email is already taken by another user
        existing = await db.get_user_by_email(request.email.lower())
        if existing and existing["id"] != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")

    # Build update data
    update_data = {}
    if request.email is not None:
        update_data["email"] = request.email.lower()
    if request.name is not None:
        update_data["name"] = request.name
    if request.is_admin is not None:
        update_data["is_admin"] = request.is_admin
    if request.is_active is not None:
        update_data["is_active"] = request.is_active

    if update_data:
        await db.update_user(user_id, **update_data)
        logger.info(f"Admin {admin['email']} updated user {user_id}")

        # If user is being promoted to admin, grant all admin permissions
        if request.is_admin is True and not user.get("is_admin"):
            perms_to_save = {k.value.lower(): v for k, v in ADMIN_PERMISSIONS.items()}
            await db.update_user(user_id, permissions=json.dumps(perms_to_save))
            logger.info(f"Admin {admin['email']} granted admin permissions to user {user_id}")
        # If user is being demoted from admin, revoke admin permissions
        elif request.is_admin is False and user.get("is_admin"):
            perms_to_save = {k.value.lower(): v for k, v in DEFAULT_USER_PERMISSIONS.items()}
            await db.update_user(user_id, permissions=json.dumps(perms_to_save))
            logger.info(f"Admin {admin['email']} revoked admin permissions from user {user_id}")

    # Update password if provided
    if request.password:
        if len(request.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        password_hash = hash_password(request.password)
        await db.update_user_password(user_id, password_hash)
        logger.info(f"Admin {admin['email']} updated password for user {user_id}")

    # Get updated user
    updated_user = await db.get_user_by_id(user_id)

    return UserResponse(
        id=updated_user["id"],
        email=updated_user["email"],
        name=updated_user.get("name"),
        is_admin=updated_user.get("is_admin", False),
        is_active=updated_user.get("is_active", True),
        created_at=updated_user["created_at"],
        last_login_at=updated_user.get("last_login_at")
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    admin: dict = Depends(require_users())
):
    """Delete user (admin only)."""
    from ..database import get_database

    db = get_database()

    # Check if user exists
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from deleting themselves
    if user_id == admin["user_id"]:
        raise HTTPException(status_code=403, detail="Cannot delete your own account")

    # Delete user
    await db.delete_user(user_id)
    logger.info(f"Admin {admin['email']} deleted user {user_id}: {user['email']}")
