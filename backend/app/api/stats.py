"""性能统计和监控 API 端点"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..database import get_database
from ..auth import require_admin

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/requests")
async def get_request_stats(
    limit: Optional[int] = Query(None, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    status_code: Optional[int] = Query(
        None, description="Filter by status code (200 for success, 400+ for errors)"
    ),
    status_min: Optional[int] = Query(
        None, description="Minimum status code (for range queries)"
    ),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_admin()),
):
    """获取请求日志统计"""
    try:
        db = get_database()

        # 如果指定了status_code，使用精确匹配
        # 如果指定了status_min（用于失败状态查询），使用范围查询
        actual_status_code = None
        if status_code is not None:
            actual_status_code = status_code

        # 保持向后兼容：如果没有提供limit参数，使用默认值1000
        effective_limit = limit if limit is not None else 1000

        logs = await db.get_request_logs(
            limit=effective_limit,
            offset=offset,
            provider_name=provider_name,
            model=model,
            status_code=actual_status_code,
            status_min=status_min,
            date_from=date_from,
            date_to=date_to,
        )

        # 获取总数（用于分页）
        total_count = await db.get_request_logs_count(
            provider_name=provider_name,
            model=model,
            status_code=actual_status_code,
            status_min=status_min,
            date_from=date_from,
            date_to=date_to,
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
            "count": len(logs),
            "total": total_count,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "page_size": limit,
            "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get request stats: {str(e)}"
        )


@router.get("/token-usage")
async def get_token_usage_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(require_admin()),
):
    """获取 Token 使用统计"""
    try:
        db = get_database()
        summary = await db.get_token_usage_summary(date_from=date_from, date_to=date_to)

        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token usage stats: {str(e)}"
        )


@router.get("/summary")
async def get_performance_summary(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: dict = Depends(require_admin())
):
    """获取性能摘要统计"""
    try:
        db = get_database()

        # 确定日期范围，如果没有提供则使用最近7天
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")

        # 获取指定时间范围内的请求日志
        logs = await db.get_request_logs(
            limit=None,
            offset=0,
            date_from=date_from,
            date_to=date_to,
        )

        # 计算统计信息
        total_requests = len(logs)
        successful_requests = sum(1 for log in logs if log.get("status_code") == 200)
        failed_requests = total_requests - successful_requests

        # 计算平均响应时间
        response_times = [
            log.get("response_time_ms") for log in logs if log.get("response_time_ms")
        ]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

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
                    "total_cost": 0,
                }

            provider_stats[provider]["total"] += 1
            if log.get("status_code") == 200:
                provider_stats[provider]["success"] += 1
            else:
                provider_stats[provider]["failed"] += 1

            # 统计所有请求的token（无论成功还是失败）
            input_tokens = log.get("input_tokens") or 0
            output_tokens = log.get("output_tokens") or 0
            provider_stats[provider]["total_tokens"] += input_tokens + output_tokens

        # 获取 Token 使用统计（使用相同的日期范围）
        token_summary = await db.get_token_usage_summary(date_from=date_from, date_to=date_to)

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
                    "total_cost": 0,
                }

            # 累加成本
            provider_stats[provider_name]["total_cost"] += cost

        return {
            "success": True,
            "data": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": (
                    (successful_requests / total_requests * 100)
                    if total_requests > 0
                    else 0
                ),
                "avg_response_time_ms": round(avg_response_time, 2),
                "provider_stats": provider_stats,
                "token_usage": token_summary,
                "date_range": {
                    "from": date_from,
                    "to": date_to
                }
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get performance summary: {str(e)}"
        )
