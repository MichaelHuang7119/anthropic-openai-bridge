"""供应商管理API端点"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel

from ..core.auth import require_admin
from ..services.provider_service import ProviderService

router = APIRouter(prefix="/api/providers", tags=["providers"])

class ProviderModel(BaseModel):
    """供应商模型"""
    name: str
    enabled: bool = True
    priority: int = 1
    api_key: str
    base_url: str
    api_version: Optional[str] = None
    timeout: int = 60
    max_retries: int = 1
    custom_headers: dict = {}
    models: dict = {}
    api_format: str = "openai"  # API format: 'openai' or 'anthropic'

# Global service instance (will be initialized in main.py)
_provider_service: Optional[ProviderService] = None


def set_provider_service(service: ProviderService):
    """Set provider service instance (called from main.py)."""
    global _provider_service
    _provider_service = service


def get_provider_service() -> ProviderService:
    """Get provider service instance."""
    if _provider_service is None:
        raise RuntimeError("Provider service not initialized. Call set_provider_service() first.")
    return _provider_service

@router.get("", response_model=List[dict])
async def get_providers(include_secrets: bool = False, user: dict = Depends(require_admin())):
    """获取所有供应商

    Args:
        include_secrets: 是否包含敏感信息（如API key），默认False
    """
    try:
        provider_service = get_provider_service()
        return provider_service.get_providers(include_secrets=include_secrets)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load providers: {str(e)}")

@router.post("", status_code=201)
async def create_provider(provider: ProviderModel, user: dict = Depends(require_admin())):
    """创建新供应商"""
    try:
        provider_service = get_provider_service()
        # Use exclude_unset=False to ensure all fields including defaults are included
        provider_service.create_provider(provider.model_dump(exclude_unset=False))
        return {"success": True, "message": "Provider created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create provider: {str(e)}")

@router.put("/{name}")
async def update_provider(
    name: str,
    provider: ProviderModel,
    api_format: Optional[str] = Query(None, description="API format for precise identification"),
    user: dict = Depends(require_admin())
):
    """更新供应商"""
    try:
        provider_service = get_provider_service()
        # Use exclude_unset=False to ensure all fields including defaults are included
        provider_dict = provider.model_dump(exclude_unset=False)

        # Use api_format from query param or from body, prioritize query param for precision
        target_api_format = api_format or provider_dict.get("api_format", "openai")

        # Log the api_format value being sent
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Update provider {name} with format {target_api_format}: received api_format = {provider_dict.get('api_format', 'NOT PROVIDED')}")

        provider_service.update_provider(name, provider_dict, target_api_format)
        return {"success": True, "message": "Provider updated successfully"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update provider: {str(e)}")

@router.patch("/{name}/enable")
async def toggle_provider_enabled(
    name: str,
    enabled: bool = Query(..., description="Enable or disable the provider"),
    api_format: Optional[str] = Query(None, description="API format for precise identification"),
    user: dict = Depends(require_admin())
):
    """切换供应商启用状态"""
    try:
        provider_service = get_provider_service()
        provider_service.toggle_provider_enabled(name, enabled, api_format)
        return {"success": True, "message": f"Provider {'enabled' if enabled else 'disabled'} successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle provider status: {str(e)}")

@router.delete("/{name}")
async def delete_provider(
    name: str,
    api_format: Optional[str] = Query(None, description="API format for precise identification"),
    user: dict = Depends(require_admin())
):
    """删除供应商"""
    try:
        provider_service = get_provider_service()
        provider_service.delete_provider(name, api_format)
        return {"success": True, "message": "Provider deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete provider: {str(e)}")

@router.post("/{name}/test")
async def test_provider(name: str, user: dict = Depends(require_admin())):
    """测试供应商连接 - 通过本地的 /v1/messages 接口测试完整流程
    
    测试所有类别（big, middle, small）的健康状态，返回每个类别的详细状态。
    """
    try:
        # Use health service to test provider
        from ..routes.health import get_health_service
        health_service = get_health_service()
        health_status = await health_service.get_provider_health_status(name)
        
        # Convert health status to test result format
        categories_result = {}
        for category, status in health_status.get("categories", {}).items():
            categories_result[category] = {
                "healthy": status.get("healthy", False),
                "responseTime": status.get("responseTime"),
                "testedModels": [],  # Not available from health check
                "workingModel": None,  # Not available from health check
                "error": status.get("error")
            }
        
        return {
            "success": True,
            "healthy": health_status.get("healthy", False),
            "categories": categories_result,
            "responseTime": health_status.get("responseTime"),
            "message": "Connection test completed" if health_status.get("healthy") else "All categories failed"
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "healthy": False,
            "categories": {},
            "responseTime": None,
            "error": str(e),
            "message": f"Connection test failed: {str(e)}"
        }