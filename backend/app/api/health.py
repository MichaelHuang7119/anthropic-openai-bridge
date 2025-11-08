"""健康检查API端点"""
from fastapi import APIRouter
from typing import List, Optional
import json
import os
import time
import asyncio
from datetime import datetime, timezone

router = APIRouter(prefix="/api/health", tags=["health"])

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

@router.get("")
async def get_all_health():
    """获取所有供应商健康状态，包括每个类别的健康状态"""
    try:
        config = load_config()
        providers = config.get("providers", [])

        health_data = []
        for p in providers:
            health_info = {
                "name": p.get("name"),
                "healthy": None,  # 未知状态
                "enabled": p.get("enabled", True),
                "priority": p.get("priority", 1),
                "lastCheck": None,
                "responseTime": None,
                "error": None,
                "categories": {}  # 每个类别的健康状态
            }

            # 如果供应商未启用，标记为不健康
            if not p.get("enabled", True):
                health_info["healthy"] = False
                health_info["error"] = "Provider is disabled"
                # 为所有类别标记为不健康
                for category in ["big", "middle", "small"]:
                    health_info["categories"][category] = {
                        "healthy": False,
                        "responseTime": None,
                        "error": "Provider is disabled"
                    }
            else:
                # 尝试快速健康检查每个类别
                # 通过 /v1/messages 接口测试完整流程，确保与实际使用场景一致
                try:
                    from app.models import MessagesRequest, Message, MessageRole
                    from app.main import _messages_internal
                    from app.circuit_breaker import get_circuit_breaker_registry
                    import time

                    # 创建模拟的 API user（健康检查不需要 API key 验证）
                    mock_api_user = {
                        "api_key_id": None,
                        "name": "health-check",
                        "email": None,
                        "user_id": None,
                        "type": "health-check"
                    }

                    # 检查熔断器状态
                    registry = get_circuit_breaker_registry()
                    breaker = registry.get_breaker(p.get("name"))
                    provider_circuit_open = breaker.state.value == "open"

                    # 获取所有模型配置
                    models = p.get("models", {})
                    
                    # 类别到 Anthropic 模型名称的映射
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
                                "error": "No models configured for this category"
                            }
                        
                        # 如果供应商的熔断器是打开的，跳过所有模型
                        if provider_circuit_open:
                            return category, {
                                "healthy": False,
                                "responseTime": None,
                                "error": "Provider circuit breaker is OPEN"
                            }
                        
                        # 获取该类别对应的 Anthropic 模型名称
                        anthropic_model_name = category_to_anthropic_model.get(category)
                        if not anthropic_model_name:
                            return category, {
                                "healthy": False,
                                "responseTime": None,
                                "error": f"Unknown category: {category}"
                            }
                        
                        # 依次尝试该类别的每个模型，直到找到一个可用的
                        # 通过 /v1/messages 接口测试，使用 exclude_models 来轮询模型
                        category_healthy = False
                        category_response_time = None
                        category_error = None
                        excluded_models_for_provider = []
                        
                        # 只测试该类别的模型，不排除其他类别的模型
                        # 这样可以避免同一模型在不同类别中的冲突
                        for model_name in category_models:
                            try:
                                # 通过 /v1/messages 接口测试完整流程
                                # 指定 provider 确保只测试当前供应商
                                # 注意：只排除当前类别中已失败的模型，不排除其他类别的模型
                                test_request = MessagesRequest(
                                    model=anthropic_model_name,
                                    provider=p.get("name"),  # 指定供应商
                                    messages=[
                                        Message(role=MessageRole.USER, content="ping")
                                    ],
                                    max_tokens=1
                                )
                                
                                # 使用 _messages_internal 测试
                                # 只排除当前类别中已失败的模型，避免影响其他类别的测试
                                test_start_time = time.time()
                                response = await _messages_internal(
                                    test_request,
                                    mock_api_user,
                                    exclude_models={p.get("name"): excluded_models_for_provider}
                                )
                                test_response_time = int((time.time() - test_start_time) * 1000)
                                
                                # 成功
                                category_healthy = True
                                category_response_time = test_response_time
                                break  # 找到一个可用的模型就停止
                                
                            except Exception as model_error:
                                # 模型测试失败，将该模型添加到排除列表，继续尝试下一个
                                excluded_models_for_provider.append(model_name)
                                error_msg = str(model_error)
                                # 提取更详细的错误信息
                                if hasattr(model_error, 'detail'):
                                    if isinstance(model_error.detail, dict):
                                        error_detail = model_error.detail.get('message', str(model_error.detail))
                                    else:
                                        error_detail = str(model_error.detail)
                                else:
                                    error_detail = str(model_error)
                                
                                if category_error is None:
                                    category_error = f"All models failed. Last error: {error_detail[:200]}"
                                # 如果所有模型都失败了，不再继续尝试
                                if len(excluded_models_for_provider) >= len(category_models):
                                    break
                                continue
                        
                        # 如果所有模型都失败了，检查是否是所有模型都被排除导致的
                        if not category_healthy and excluded_models_for_provider == category_models:
                            # 所有模型都被排除了，这意味着所有模型都失败了
                            # 这可能是由于速率限制或其他临时错误
                            # 不改变 category_error，因为它已经包含了最后一个错误信息
                            pass
                        
                        return category, {
                            "healthy": category_healthy,
                            "responseTime": category_response_time,
                            "error": category_error if not category_healthy else None
                        }
                    
                    # 并行测试所有类别
                    category_tasks = [test_category(cat) for cat in ["big", "middle", "small"]]
                    category_results = await asyncio.gather(*category_tasks)
                    
                    # 将结果转换为字典
                    category_health = {}
                    overall_healthy = False
                    overall_response_time = None
                    
                    for category, result in category_results:
                        category_health[category] = result
                        if result["healthy"]:
                            overall_healthy = True
                            if overall_response_time is None:
                                overall_response_time = result["responseTime"]
                    
                    health_info["healthy"] = overall_healthy
                    health_info["responseTime"] = overall_response_time
                    health_info["categories"] = category_health
                    health_info["lastCheck"] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                    
                    if not overall_healthy:
                        # 如果所有类别都不健康，记录错误信息
                        errors = []
                        for cat, status in category_health.items():
                            if not status.get("healthy") and status.get("error"):
                                errors.append(f"{cat}: {status['error']}")
                        if errors:
                            health_info["error"] = "; ".join(errors)[:200]
                            
                except Exception as e:
                    health_info["healthy"] = False
                    health_info["error"] = str(e)[:200]  # 截断错误信息
                    health_info["lastCheck"] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                    # 为所有类别标记为不健康
                    for category in ["big", "middle", "small"]:
                        health_info["categories"][category] = {
                            "healthy": False,
                            "responseTime": None,
                            "error": str(e)[:100]
                        }

            health_data.append(health_info)

        # 计算总体状态：
        # - 如果所有启用的供应商都是健康的 → "healthy" (健康)
        # - 如果有健康的也有不健康的 → "partial" (部分健康)
        # - 如果所有启用的供应商都不健康 → "unhealthy" (不健康)
        # - 如果没有启用的供应商或检查出错 → "error" (未检查)
        enabled_providers = [h for h in health_data if h.get("enabled", True)]
        if not enabled_providers:
            overall_status = "error"
        else:
            healthy_providers = [h for h in enabled_providers if h["healthy"] is True]
            unhealthy_providers = [h for h in enabled_providers if h["healthy"] is False]
            
            if len(healthy_providers) == len(enabled_providers) and len(unhealthy_providers) == 0:
                # 所有启用的供应商都健康
                overall_status = "healthy"
            elif len(healthy_providers) > 0 and len(unhealthy_providers) > 0:
                # 有健康的也有不健康的
                overall_status = "partial"
            elif len(unhealthy_providers) == len(enabled_providers) and len(healthy_providers) == 0:
                # 所有启用的供应商都不健康
                overall_status = "unhealthy"
            else:
                # 有未知状态的供应商
                overall_status = "error"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec='seconds'),
            "providers": health_data
        }
    except Exception as e:
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
        config = load_config()
        provider_data = None

        # 找到供应商
        for p in config.get("providers", []):
            if p.get("name") == name:
                provider_data = p
                break

        if not provider_data:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Provider not found")

        health_info = {
            "name": name,
            "healthy": None,
            "enabled": provider_data.get("enabled", True),
            "priority": provider_data.get("priority", 1),
            "lastCheck": None,
            "responseTime": None,
            "error": None,
            "categories": {}  # 每个类别的健康状态
        }

        if not provider_data.get("enabled", True):
            health_info["healthy"] = False
            health_info["error"] = "Provider is disabled"
            # 为所有类别标记为不健康
            for category in ["big", "middle", "small"]:
                health_info["categories"][category] = {
                    "healthy": False,
                    "responseTime": None,
                    "error": "Provider is disabled"
                }
        else:
            try:
                from app.models import MessagesRequest, Message, MessageRole
                from app.main import _messages_internal
                from app.circuit_breaker import get_circuit_breaker_registry

                # 创建模拟的 API user（健康检查不需要 API key 验证）
                mock_api_user = {
                    "api_key_id": None,
                    "name": "health-check",
                    "email": None,
                    "user_id": None,
                    "type": "health-check"
                }

                # 检查熔断器状态
                registry = get_circuit_breaker_registry()
                breaker = registry.get_breaker(name)
                provider_circuit_open = breaker.state.value == "open"

                # 获取所有模型配置
                models = provider_data.get("models", {})
                
                # 类别到 Anthropic 模型名称的映射
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
                            "error": "No models configured for this category"
                        }
                    
                    # 如果供应商的熔断器是打开的，跳过所有模型
                    if provider_circuit_open:
                        return category, {
                            "healthy": False,
                            "responseTime": None,
                            "error": "Provider circuit breaker is OPEN"
                        }
                    
                    # 获取该类别对应的 Anthropic 模型名称
                    anthropic_model_name = category_to_anthropic_model.get(category)
                    if not anthropic_model_name:
                        return category, {
                            "healthy": False,
                            "responseTime": None,
                            "error": f"Unknown category: {category}"
                        }
                    
                    # 依次尝试该类别的每个模型，直到找到一个可用的
                    # 通过 /v1/messages 接口测试，使用 exclude_models 来轮询模型
                    category_healthy = False
                    category_response_time = None
                    category_error = None
                    excluded_models_for_provider = []
                    
                    for model_name in category_models:
                        try:
                            # 通过 /v1/messages 接口测试完整流程
                            # 指定 provider 确保只测试当前供应商
                            test_request = MessagesRequest(
                                model=anthropic_model_name,
                                provider=name,  # 指定供应商
                                messages=[
                                    Message(role=MessageRole.USER, content="ping")
                                ],
                                max_tokens=1
                            )
                            
                            # 使用 _messages_internal 测试，传递 exclude_models 来轮询模型
                            test_start_time = time.time()
                            response = await _messages_internal(
                                test_request,
                                mock_api_user,
                                exclude_models={name: excluded_models_for_provider}
                            )
                            test_response_time = int((time.time() - test_start_time) * 1000)
                            
                            # 成功
                            category_healthy = True
                            category_response_time = test_response_time
                            break  # 找到一个可用的模型就停止
                            
                        except Exception as model_error:
                            # 模型测试失败，将该模型添加到排除列表，继续尝试下一个
                            excluded_models_for_provider.append(model_name)
                            # 提取更详细的错误信息
                            if hasattr(model_error, 'detail'):
                                if isinstance(model_error.detail, dict):
                                    error_detail = model_error.detail.get('message', str(model_error.detail))
                                else:
                                    error_detail = str(model_error.detail)
                            else:
                                error_detail = str(model_error)
                            
                            if category_error is None:
                                category_error = f"All models failed. Last error: {error_detail[:200]}"
                            # 如果所有模型都失败了，不再继续尝试
                            if len(excluded_models_for_provider) >= len(category_models):
                                break
                            continue
                    
                    return category, {
                        "healthy": category_healthy,
                        "responseTime": category_response_time,
                        "error": category_error if not category_healthy else None
                    }
                
                # 并行测试所有类别
                category_tasks = [test_category(cat) for cat in ["big", "middle", "small"]]
                category_results = await asyncio.gather(*category_tasks)
                
                # 将结果转换为字典并计算总体状态
                category_health = {}
                overall_healthy = False
                overall_response_time = None
                
                for category, result in category_results:
                    category_health[category] = result
                    if result["healthy"]:
                        overall_healthy = True
                        if overall_response_time is None:
                            overall_response_time = result["responseTime"]
                
                health_info["healthy"] = overall_healthy
                health_info["responseTime"] = overall_response_time
                health_info["categories"] = category_health
                health_info["lastCheck"] = datetime.now(timezone.utc).isoformat()
                
                if not overall_healthy:
                    # 如果所有类别都不健康，记录错误信息
                    errors = []
                    for cat, status in category_health.items():
                        if not status.get("healthy") and status.get("error"):
                            errors.append(f"{cat}: {status['error']}")
                    if errors:
                        health_info["error"] = "; ".join(errors)[:200]
                        
            except Exception as e:
                health_info["healthy"] = False
                health_info["error"] = str(e)[:200]
                health_info["lastCheck"] = datetime.now(timezone.utc).isoformat()
                # 为所有类别标记为不健康
                for category in ["big", "middle", "small"]:
                    health_info["categories"][category] = {
                        "healthy": False,
                        "responseTime": None,
                        "error": str(e)[:100]
                    }

        return health_info
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))