"""性能统计和监控 API 端点"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from ..database import get_database
from ..core.auth import require_admin
from ..core import COST_PER_INPUT_TOKEN, COST_PER_OUTPUT_TOKEN

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

        # 按供应商统计 - 首先基于 request_logs 表统计所有数据
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

            # 统计所有请求的token（无论成功还是失败）并计算成本
            input_tokens = log.get("input_tokens") or 0
            output_tokens = log.get("output_tokens") or 0
            total_request_tokens = input_tokens + output_tokens
            provider_stats[provider]["total_tokens"] += total_request_tokens

            # 同时计算该请求的成本并累加
            request_cost = (input_tokens * COST_PER_INPUT_TOKEN) + (output_tokens * COST_PER_OUTPUT_TOKEN)
            provider_stats[provider]["total_cost"] += request_cost

        # 构建基于 request_logs 的准确 token_usage 统计
        # 按日期和供应商聚合 request_logs 数据，生成准确的 token 使用统计
        accurate_token_usage = {
            "summary": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_estimate": 0,
            "date_range": {
                "from": date_from,
                "to": date_to
            }
        }

        # 按日期和供应商聚合日志数据
        date_provider_map = {}
        for log in logs:
            created_at = log.get("created_at")
            log_date = None

            if created_at:
                # 处理不同格式的日期时间字段
                if isinstance(created_at, str):
                    # 如果是字符串格式，提取日期部分 (YYYY-MM-DD)
                    log_date = created_at[:10]
                elif hasattr(created_at, 'strftime'):
                    # 如果是datetime对象，格式化为字符串
                    log_date = created_at.strftime("%Y-%m-%d")
                elif isinstance(created_at, (int, float)):
                    # 如果是时间戳，转换为datetime然后格式化
                    from datetime import datetime as dt
                    dt_obj = dt.fromtimestamp(created_at)
                    log_date = dt_obj.strftime("%Y-%m-%d")

            # 如果无法获取有效日期，跳过此记录
            if not log_date:
                # 记录调试信息
                print(f"Warning: Could not parse date for log: {log.get('request_id', 'unknown')}, created_at: {created_at}")
                continue

            provider = log.get("provider_name", "unknown")
            model = log.get("model", "unknown")
            input_tokens = log.get("input_tokens") or 0
            output_tokens = log.get("output_tokens") or 0
            request_cost = (input_tokens * COST_PER_INPUT_TOKEN) + (output_tokens * COST_PER_OUTPUT_TOKEN)

            key = (log_date, provider)
            if key not in date_provider_map:
                date_provider_map[key] = {
                    "date": log_date,
                    "provider_name": provider,
                    "model": model,
                    "request_count": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_cost_estimate": 0
                }

            date_provider_map[key]["request_count"] += 1
            date_provider_map[key]["total_input_tokens"] += input_tokens
            date_provider_map[key]["total_output_tokens"] += output_tokens
            date_provider_map[key]["total_cost_estimate"] += request_cost

        # 构建准确的摘要
        for item in date_provider_map.values():
            accurate_token_usage["summary"].append(item)
            accurate_token_usage["total_input_tokens"] += item["total_input_tokens"]
            accurate_token_usage["total_output_tokens"] += item["total_output_tokens"]
            accurate_token_usage["total_cost_estimate"] += item["total_cost_estimate"]

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
                "token_usage": accurate_token_usage,
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
