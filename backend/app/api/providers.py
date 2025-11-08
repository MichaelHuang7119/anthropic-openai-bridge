"""供应商管理API端点"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import json
import os

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

def get_config_path():
    """获取配置文件路径"""
    return os.getenv(
        "PROVIDER_CONFIG_PATH",
        str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/provider.json"
    )

def load_config():
    """加载配置文件"""
    config_path = get_config_path()
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(data):
    """保存配置文件"""
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@router.get("", response_model=List[dict])
async def get_providers(include_secrets: bool = False):
    """获取所有供应商

    Args:
        include_secrets: 是否包含敏感信息（如API key），默认False
    """
    try:
        config = load_config()
        providers = []

        for p in config.get("providers", []):
            provider = {
                "name": p.get("name"),
                "enabled": p.get("enabled", True),
                "priority": p.get("priority", 1),
                "base_url": p.get("base_url"),
                "api_version": p.get("api_version"),
                "timeout": p.get("timeout", 60),
                "max_retries": p.get("max_retries", 1),
                "custom_headers": p.get("custom_headers", {}),
                "models": p.get("models", {})
            }

            # 只有在明确要求时才显示 API key
            if include_secrets:
                provider["api_key"] = p.get("api_key", "")
            else:
                # 隐藏API key以保护敏感信息
                provider["api_key"] = "***" if p.get("api_key") else ""

            providers.append(provider)

        return providers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load providers: {str(e)}")

@router.post("", status_code=201)
async def create_provider(provider: ProviderModel):
    """创建新供应商"""
    try:
        config = load_config()

        # 验证供应商名称唯一
        for p in config.get("providers", []):
            if p.get("name") == provider.name:
                raise HTTPException(status_code=400, detail="Provider already exists")

        # 添加到配置
        provider_dict = provider.model_dump()
        config.setdefault("providers", []).append(provider_dict)

        # 保存
        save_config(config)

        return {"success": True, "message": "Provider created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create provider: {str(e)}")

@router.put("/{name}")
async def update_provider(name: str, provider: ProviderModel):
    """更新供应商"""
    try:
        config = load_config()
        providers = config.get("providers", [])

        # 找到并更新供应商
        for i, p in enumerate(providers):
            if p.get("name") == name:
                # 检查新名称是否冲突
                if provider.name != name:
                    for j, other in enumerate(providers):
                        if j != i and other.get("name") == provider.name:
                            raise HTTPException(status_code=400, detail="Provider name already exists")

                # 更新
                provider_dict = provider.model_dump()
                providers[i] = provider_dict
                config["providers"] = providers

                # 保存
                save_config(config)

                return {"success": True, "message": "Provider updated successfully"}

        raise HTTPException(status_code=404, detail="Provider not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update provider: {str(e)}")

@router.delete("/{name}")
async def delete_provider(name: str):
    """删除供应商"""
    try:
        config = load_config()
        providers = config.get("providers", [])

        # 找到并删除
        for i, p in enumerate(providers):
            if p.get("name") == name:
                del providers[i]
                config["providers"] = providers

                # 保存
                save_config(config)

                return {"success": True, "message": "Provider deleted successfully"}

        raise HTTPException(status_code=404, detail="Provider not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete provider: {str(e)}")

@router.post("/{name}/test")
async def test_provider(name: str):
    """测试供应商连接"""
    try:
        config = load_config()
        provider_data = None

        # 找到供应商
        for p in config.get("providers", []):
            if p.get("name") == name:
                provider_data = p
                break

        if not provider_data:
            raise HTTPException(status_code=404, detail="Provider not found")

        # 导入客户端
        from app.client import OpenAIClient

        # 创建临时配置对象
        class TempProvider:
            def __init__(self, data):
                self.name = data.get("name")
                self.api_key = data.get("api_key")
                self.base_url = data.get("base_url")
                self.timeout = data.get("timeout", 60)
                self.max_retries = data.get("max_retries", 1)

        provider = TempProvider(provider_data)
        client = OpenAIClient(provider)

        # 尝试简单的请求测试连接
        models = provider_data.get("models", {})
        small_models = models.get("small", [])

        if not small_models:
            # 如果没有small模型，尝试任何可用模型
            for category in ["big", "middle", "small"]:
                if models.get(category):
                    small_models = models[category]
                    break

        if not small_models:
            raise HTTPException(status_code=400, detail="No models configured")

        # 测试请求
        import time
        start_time = time.time()

        try:
            response = client.chat_completion(
                model=small_models[0],
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )

            response_time = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "healthy": True,
                "responseTime": response_time,
                "message": "Connection successful"
            }
        except Exception as api_error:
            # API调用失败
            response_time = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "healthy": False,
                "responseTime": response_time,
                "error": str(api_error),
                "message": f"Connection failed: {str(api_error)}"
            }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "healthy": False,
            "responseTime": None,
            "error": str(e),
            "message": f"Connection test failed: {str(e)}"
        }