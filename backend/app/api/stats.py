"""性能统计和监控 API 端点"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..database import get_database
from ..auth import require_admin

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/requests")
async def get_request_stats(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    provider_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_admin())
):
    """获取请求日志统计"""
    try:
        db = get_database()
        logs = await db.get_request_logs(
            limit=limit,
            offset=offset,
            provider_name=provider_name,
            date_from=date_from,
            date_to=date_to
        )
        
        # 解析 JSON 字段
        for log in logs:
            if log.get("request_params"):
                try:
                    import json
                    log["request_params"] = json.loads(log["request_params"])
                except:
                    pass
            if log.get("response_data"):
                try:
                    import json
                    log["response_data"] = json.loads(log["response_data"])
                except:
                    pass
        
        return {
            "success": True,
            "data": logs,
            "count": len(logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get request stats: {str(e)}")


@router.get("/token-usage")
async def get_token_usage_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_admin())
):
    """获取 Token 使用统计"""
    try:
        db = get_database()
        summary = await db.get_token_usage_summary(
            date_from=date_from,
            date_to=date_to
        )
        
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token usage stats: {str(e)}")


@router.get("/summary")
async def get_performance_summary(user: dict = Depends(require_admin())):
    """获取性能摘要统计"""
    try:
        db = get_database()
        
        # 获取最近 24 小时的请求日志
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        logs = await db.get_request_logs(
            limit=1000,
            offset=0,
            date_from=yesterday
        )
        
        # 计算统计信息
        total_requests = len(logs)
        successful_requests = sum(1 for log in logs if log.get("status_code") == 200)
        failed_requests = total_requests - successful_requests
        
        # 计算平均响应时间
        response_times = [log.get("response_time_ms") for log in logs if log.get("response_time_ms")]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # 按供应商统计
        provider_stats: Dict[str, Dict[str, Any]] = {}
        for log in logs:
            provider = log.get("provider_name", "unknown")
            if provider not in provider_stats:
                provider_stats[provider] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "total_tokens": 0,
                    "total_cost": 0
                }
            
            provider_stats[provider]["total"] += 1
            if log.get("status_code") == 200:
                provider_stats[provider]["success"] += 1
            else:
                provider_stats[provider]["failed"] += 1
            
            input_tokens = log.get("input_tokens") or 0
            output_tokens = log.get("output_tokens") or 0
            provider_stats[provider]["total_tokens"] += input_tokens + output_tokens
        
        # 获取 Token 使用统计
        token_summary = await db.get_token_usage_summary(date_from=yesterday)
        
        # 从 token_usage 表中按供应商汇总成本
        for usage_item in token_summary.get("summary", []):
            provider_name = usage_item.get("provider_name", "unknown")
            cost = usage_item.get("total_cost_estimate", 0)
            
            # 如果供应商不在 provider_stats 中，初始化它
            if provider_name not in provider_stats:
                provider_stats[provider_name] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "total_tokens": 0,
                    "total_cost": 0
                }
            
            # 累加成本
            provider_stats[provider_name]["total_cost"] += cost
        
        return {
            "success": True,
            "data": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                "avg_response_time_ms": round(avg_response_time, 2),
                "provider_stats": provider_stats,
                "token_usage": token_summary
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance summary: {str(e)}")

