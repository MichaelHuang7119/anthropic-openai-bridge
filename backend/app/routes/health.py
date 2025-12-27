"""健康检查API端点"""
from fastapi import APIRouter, HTTPException
from typing import Optional

from ..services.health_service import HealthService

router = APIRouter(prefix="/api/health", tags=["health"])

# Global service instances (will be initialized in main.py)
_health_service: Optional[HealthService] = None


def set_health_service(service: HealthService):
    """Set health service instance (called from main.py)."""
    global _health_service
    _health_service = service


def get_health_service() -> HealthService:
    """Get health service instance."""
    if _health_service is None:
        raise RuntimeError("Health service not initialized. Call set_health_service() first.")
    return _health_service


@router.get("")
async def get_all_health():
    """获取所有供应商健康状态，包括每个类别的健康状态"""
    try:
        health_service = get_health_service()
        health_data = await health_service.get_all_health_status()
        # Save health status to database after getting the data
        await health_service.save_health_status_to_db(health_data)
        return health_data
    except Exception as e:
        from datetime import datetime, timezone
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec='seconds'),
            "error": str(e),
            "providers": []
        }


@router.get("/latest")
async def get_latest_health():
    """从数据库获取最新的健康检查结果（不进行新的检查）"""
    try:
        health_service = get_health_service()
        health_data = await health_service.get_latest_health_from_db()
        if health_data:
            return health_data
        else:
            from datetime import datetime, timezone
            return {
                "status": "not_checked",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec='seconds'),
                "message": "No health check data available. Please perform a health check first.",
                "providers": []
            }
    except Exception as e:
        from datetime import datetime, timezone
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec='seconds'),
            "error": str(e),
            "providers": []
        }



@router.get("/{name}")
async def get_provider_health(name: str):
    """获取单个供应商健康状态，包括每个类别的健康状态"""
    try:
        health_service = get_health_service()
        return await health_service.get_provider_health_status(name)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
