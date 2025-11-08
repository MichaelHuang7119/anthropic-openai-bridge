"""健康检查API端点"""
from fastapi import APIRouter
from typing import List, Optional
import json
import os
import time

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
    """获取所有供应商健康状态"""
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
                "error": None
            }

            # 如果供应商未启用，标记为不健康
            if not p.get("enabled", True):
                health_info["healthy"] = False
                health_info["error"] = "Provider is disabled"
            else:
                # 尝试快速健康检查
                try:
                    from app.client import OpenAIClient

                    class TempProvider:
                        def __init__(self, data):
                            self.name = data.get("name")
                            self.api_key = data.get("api_key")
                            self.base_url = data.get("base_url")
                            self.timeout = 5  # 使用较短的超时时间
                            self.max_retries = 0  # 不重试

                    provider = TempProvider(p)
                    client = OpenAIClient(provider)

                    # 获取一个可用模型
                    models = p.get("models", {})
                    test_model = None
                    for category in ["small", "middle", "big"]:
                        if models.get(category):
                            test_model = models[category][0]
                            break

                    if test_model:
                        start_time = time.time()
                        # 发送最小请求测试连接
                        response = client.chat_completion(
                            model=test_model,
                            messages=[{"role": "user", "content": "ping"}],
                            max_tokens=1
                        )
                        response_time = int((time.time() - start_time) * 1000)

                        health_info["healthy"] = True
                        health_info["responseTime"] = response_time
                        health_info["lastCheck"] = time.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    health_info["healthy"] = False
                    health_info["error"] = str(e)[:200]  # 截断错误信息
                    health_info["lastCheck"] = time.strftime("%Y-%m-%d %H:%M:%S")

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
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "providers": health_data
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error": str(e),
            "providers": []
        }

@router.get("/{name}")
async def get_provider_health(name: str):
    """获取单个供应商健康状态"""
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
            "error": None
        }

        if not provider_data.get("enabled", True):
            health_info["healthy"] = False
            health_info["error"] = "Provider is disabled"
        else:
            try:
                from app.client import OpenAIClient

                class TempProvider:
                    def __init__(self, data):
                        self.name = data.get("name")
                        self.api_key = data.get("api_key")
                        self.base_url = data.get("base_url")
                        self.timeout = 5
                        self.max_retries = 0

                provider = TempProvider(provider_data)
                client = OpenAIClient(provider)

                # 获取可用模型
                models = provider_data.get("models", {})
                test_model = None
                for category in ["small", "middle", "big"]:
                    if models.get(category):
                        test_model = models[category][0]
                        break

                if not test_model:
                    health_info["healthy"] = False
                    health_info["error"] = "No models configured"
                else:
                    start_time = time.time()
                    response = client.chat_completion(
                        model=test_model,
                        messages=[{"role": "user", "content": "ping"}],
                        max_tokens=1
                    )
                    response_time = int((time.time() - start_time) * 1000)

                    health_info["healthy"] = True
                    health_info["responseTime"] = response_time
                    health_info["lastCheck"] = time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                health_info["healthy"] = False
                health_info["error"] = str(e)[:200]
                health_info["lastCheck"] = time.strftime("%Y-%m-%d %H:%M:%S")

        return health_info
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))