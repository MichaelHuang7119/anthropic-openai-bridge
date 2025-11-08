"""供应商管理API端点"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
import json
import os
import asyncio
from ..config import config
from ..auth import require_admin

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
async def get_providers(include_secrets: bool = False, user: dict = Depends(require_admin())):
    """获取所有供应商

    Args:
        include_secrets: 是否包含敏感信息（如API key），默认False
    """
    try:
        config_data = load_config()
        providers = []

        for p in config_data.get("providers", []):
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
async def create_provider(provider: ProviderModel, user: dict = Depends(require_admin())):
    """创建新供应商"""
    try:
        config_data = load_config()

        # 验证供应商名称唯一
        for p in config_data.get("providers", []):
            if p.get("name") == provider.name:
                raise HTTPException(status_code=400, detail="Provider already exists")

        # 添加到配置
        provider_dict = provider.model_dump()
        config_data.setdefault("providers", []).append(provider_dict)

        # 保存
        save_config(config_data)

        # 重新加载全局配置，确保 model_manager 使用最新配置
        config._load_config()

        return {"success": True, "message": "Provider created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create provider: {str(e)}")

@router.put("/{name}")
async def update_provider(name: str, provider: ProviderModel, user: dict = Depends(require_admin())):
    """更新供应商"""
    try:
        config_data = load_config()
        providers = config_data.get("providers", [])

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
                config_data["providers"] = providers

                # 保存
                save_config(config_data)

                # 重新加载全局配置，确保 model_manager 使用最新配置
                config._load_config()

                return {"success": True, "message": "Provider updated successfully"}

        raise HTTPException(status_code=404, detail="Provider not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update provider: {str(e)}")

@router.patch("/{name}/enable")
async def toggle_provider_enabled(
    name: str, 
    enabled: bool = Query(..., description="Enable or disable the provider"),
    user: dict = Depends(require_admin())
):
    """切换供应商启用状态"""
    try:
        config_data = load_config()
        providers = config_data.get("providers", [])

        # 找到并更新供应商的启用状态
        for i, p in enumerate(providers):
            if p.get("name") == name:
                providers[i]["enabled"] = enabled
                config_data["providers"] = providers

                # 保存
                save_config(config_data)

                # 重新加载全局配置，确保 model_manager 使用最新配置
                config._load_config()

                return {"success": True, "message": f"Provider {'enabled' if enabled else 'disabled'} successfully"}

        raise HTTPException(status_code=404, detail="Provider not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle provider status: {str(e)}")

@router.delete("/{name}")
async def delete_provider(name: str, user: dict = Depends(require_admin())):
    """删除供应商"""
    try:
        config_data = load_config()
        providers = config_data.get("providers", [])

        # 找到并删除
        for i, p in enumerate(providers):
            if p.get("name") == name:
                del providers[i]
                config_data["providers"] = providers

                # 保存
                save_config(config_data)

                # 重新加载全局配置，确保 model_manager 使用最新配置
                config._load_config()

                return {"success": True, "message": "Provider deleted successfully"}

        raise HTTPException(status_code=404, detail="Provider not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete provider: {str(e)}")

@router.post("/{name}/test")
async def test_provider(name: str, user: dict = Depends(require_admin())):
    """测试供应商连接 - 通过本地的 /v1/messages 接口测试完整流程
    
    测试所有类别（big, middle, small）的健康状态，返回每个类别的详细状态。
    """
    try:
        config_data = load_config()
        provider_data = None

        # 找到供应商
        for p in config_data.get("providers", []):
            if p.get("name") == name:
                provider_data = p
                break

        if not provider_data:
            raise HTTPException(status_code=404, detail="Provider not found")

        # 检查供应商是否启用
        if not provider_data.get("enabled", True):
            return {
                "success": False,
                "healthy": False,
                "categories": {},
                "responseTime": None,
                "message": "Provider is disabled"
            }

        # 导入必要的模块
        from app.models import MessagesRequest, Message, MessageRole
        from app.main import _messages_internal, model_manager
        from app.circuit_breaker import get_circuit_breaker_registry
        from app.config import config
        import time

        # 创建模拟的 API user（测试接口已经有 admin 权限，所以可以绕过 API key 验证）
        mock_api_user = {
            "api_key_id": None,
            "name": "test-user",
            "email": None,
            "user_id": None,
            "type": "test"
        }

        # 获取所有模型配置
        models = provider_data.get("models", {})
        
        # 检查熔断器状态
        registry = get_circuit_breaker_registry()
        breaker = registry.get_breaker(name)
        provider_circuit_open = breaker.state.value == "open"
        
        # 类别到 Anthropic 模型名称的映射
        # 用于通过 /v1/messages 接口测试，该接口期望 Anthropic 格式的模型名称
        category_to_anthropic_model = {
            "big": "opus",
            "middle": "sonnet",
            "small": "haiku"
        }
        
        # 并行测试所有类别
        async def test_category(category: str):
            """测试单个类别的健康状态"""
            category_models = models.get(category, [])
            
            if not category_models:
                return category, {
                    "healthy": False,
                    "responseTime": None,
                    "testedModels": [],
                    "workingModel": None,
                    "error": "No models configured for this category"
                }
            
            # 如果供应商的熔断器是打开的，跳过所有模型
            if provider_circuit_open:
                return category, {
                    "healthy": False,
                    "responseTime": None,
                    "testedModels": category_models,
                    "workingModel": None,
                    "error": f"Provider circuit breaker is OPEN"
                }
            
            # 获取该类别对应的 Anthropic 模型名称
            anthropic_model_name = category_to_anthropic_model.get(category)
            if not anthropic_model_name:
                return category, {
                    "healthy": False,
                    "responseTime": None,
                    "testedModels": category_models,
                    "workingModel": None,
                    "error": f"Unknown category: {category}"
                }
            
            # 验证该供应商是否配置了该类别的模型
            if category not in models or not models[category]:
                return category, {
                    "healthy": False,
                    "responseTime": None,
                    "testedModels": [],
                    "workingModel": None,
                    "error": f"No models configured for category '{category}'"
                }
            
            # 依次尝试该类别的每个模型
            # 通过 /v1/messages 接口测试，使用 Anthropic 模型名称
            # 使用 exclude_models 参数来依次测试每个模型
            # 同时指定 provider 参数，确保只测试当前供应商
            category_healthy = False
            category_response_time = None
            working_model = None
            tested_models = []
            category_error = None
            excluded_models_for_provider = []
            
            for model_name in category_models:
                tested_models.append(model_name)
                
                try:
                    # 通过 /v1/messages 接口测试完整流程
                    # 使用 Anthropic 模型名称，并指定 provider 确保只测试当前供应商
                    # 使用 exclude_models 来排除之前测试失败的模型，确保测试当前模型
                    test_request = MessagesRequest(
                        model=anthropic_model_name,
                        provider=name,  # 指定供应商，确保只测试当前供应商
                        messages=[
                            Message(role=MessageRole.USER, content="ping")
                        ],
                        max_tokens=1
                    )
                    
                    # 测试请求 - 使用 _messages_internal 并传递 exclude_models
                    # 这样可以依次测试该类别的每个模型
                    test_start_time = time.time()
                    response = await _messages_internal(
                        test_request,
                        mock_api_user,
                        exclude_models={name: excluded_models_for_provider}
                    )
                    test_response_time = int((time.time() - test_start_time) * 1000)
                    
                    # 成功 - 获取实际使用的模型名称
                    # 从 model_manager 获取实际选择的模型（排除已测试的模型后）
                    try:
                        actual_provider, actual_model = model_manager.get_provider_and_model(
                            anthropic_model_name,
                            exclude_models={name: excluded_models_for_provider},
                            preferred_provider=name  # 指定供应商
                        )
                        # 验证实际选择的模型是否在当前测试的模型列表中
                        if actual_model in category_models:
                            working_model = actual_model
                        else:
                            # 如果实际选择的模型不在列表中，使用当前测试的模型名称
                            working_model = model_name
                    except:
                        # 如果无法获取实际模型，使用当前测试的模型名称
                        working_model = model_name
                    
                    category_healthy = True
                    category_response_time = test_response_time
                    break  # 找到一个可用的模型就停止
                    
                except Exception as model_error:
                    # 模型测试失败，将该模型添加到排除列表，继续尝试下一个
                    excluded_models_for_provider.append(model_name)
                    error_msg = str(model_error)
                    if category_error is None:
                        category_error = f"All models failed. Last error: {error_msg}"
                    else:
                        category_error = f"All models failed. Last error: {error_msg}"
                    continue
            
            return category, {
                "healthy": category_healthy,
                "responseTime": category_response_time,
                "testedModels": tested_models,
                "workingModel": working_model,
                "error": category_error if not category_healthy else None
            }
        
        # 并行测试所有类别
        category_tasks = [test_category(cat) for cat in ["big", "middle", "small"]]
        category_results = await asyncio.gather(*category_tasks)
        
        # 将结果转换为字典并计算总体状态
        categories_result = {}
        overall_healthy = False
        overall_response_time = None
        
        for category, result in category_results:
            categories_result[category] = result
            if result["healthy"]:
                overall_healthy = True
                if overall_response_time is None:
                    overall_response_time = result["responseTime"]
        
        # 构造返回结果
        return {
            "success": True,
            "healthy": overall_healthy,
            "categories": categories_result,
            "responseTime": overall_response_time,
            "message": "Connection test completed" if overall_healthy else "All categories failed"
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