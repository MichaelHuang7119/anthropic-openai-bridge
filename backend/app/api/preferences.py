"""用户偏好设置API端点"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ..auth import require_admin
from ..database import get_database

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


class LanguagePreferenceModel(BaseModel):
    """语言偏好模型"""
    language: str = Field(..., description="语言代码，如 en-US, zh-CN")


@router.get("/language", response_model=LanguagePreferenceModel)
async def get_language_preference(user: dict = Depends(require_admin())):
    """获取用户语言偏好"""
    try:
        db = get_database()
        language = await db.get_user_language(user['user_id'])

        return {"language": language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get language preference: {str(e)}")


@router.put("/language", response_model=dict)
async def update_language_preference(
    preference: LanguagePreferenceModel,
    user: dict = Depends(require_admin())
):
    """更新用户语言偏好"""
    try:
        db = get_database()
        await db.update_user_language(user['user_id'], preference.language)

        return {
            "success": True,
            "message": "Language preference updated successfully",
            "language": preference.language
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update language preference: {str(e)}")
