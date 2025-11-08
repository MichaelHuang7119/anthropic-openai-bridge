"""全局配置API端点"""
from fastapi import APIRouter, HTTPException
import json
import os
from pydantic import BaseModel

router = APIRouter(prefix="/api/config", tags=["config"])

class CircuitBreakerConfig(BaseModel):
    """断路器配置"""
    failure_threshold: int = 5
    recovery_timeout: int = 60

class GlobalConfigModel(BaseModel):
    """全局配置模型"""
    fallback_strategy: str = "priority"
    circuit_breaker: CircuitBreakerConfig

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

@router.get("", response_model=dict)
async def get_global_config():
    """获取全局配置"""
    try:
        config = load_config()

        # 提取全局配置
        global_config = {
            "fallback_strategy": config.get("fallback_strategy", "priority"),
            "circuit_breaker": config.get("circuit_breaker", {
                "failure_threshold": 5,
                "recovery_timeout": 60
            })
        }

        return global_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {str(e)}")

@router.put("")
async def update_global_config(config_model: GlobalConfigModel):
    """更新全局配置"""
    try:
        config = load_config()

        # 更新全局配置
        config["fallback_strategy"] = config_model.fallback_strategy
        config["circuit_breaker"] = config_model.circuit_breaker.model_dump()

        # 保存
        save_config(config)

        return {"success": True, "message": "Config updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")