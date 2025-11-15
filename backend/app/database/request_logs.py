"""Request logs database operations."""
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class RequestLogsManager:
    """Manages request logs in the database."""

    def __init__(self, db_core):
        """
        Initialize request logs manager.

        Args:
            db_core: DatabaseCore instance for connection management.
        """
        self.db_core = db_core

    async def log_request(
        self,
        request_id: str,
        provider_name: str,
        model: str,
        request_params: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        response_time_ms: Optional[float] = None
    ):
        """Log a request to the database."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO request_logs (
                    request_id, provider_name, model, request_params, response_data,
                    status_code, error_message, input_tokens, output_tokens, response_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request_id,
                provider_name,
                model,
                json.dumps(request_params, ensure_ascii=False),
                json.dumps(response_data, ensure_ascii=False) if response_data else None,
                status_code,
                error_message,
                input_tokens,
                output_tokens,
                response_time_ms
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log request: {e}")

    async def get_request_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        status_min: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get request logs with optional filters."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM request_logs WHERE 1=1"
            params = []

            if provider_name:
                query += " AND provider_name = ?"
                params.append(provider_name)

            if model:
                query += " AND model = ?"
                params.append(model)

            if status_code is not None:
                query += " AND status_code = ?"
                params.append(status_code)
            elif status_min is not None:
                query += " AND status_code >= ?"
                params.append(status_min)

            if date_from:
                query += " AND date(created_at) >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date(created_at) <= ?"
                params.append(date_to)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get request logs: {e}")
            return []

    async def get_request_logs_count(
        self,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        status_min: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> int:
        """Get total count of request logs matching filters."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            query = "SELECT COUNT(*) as count FROM request_logs WHERE 1=1"
            params = []

            if provider_name:
                query += " AND provider_name = ?"
                params.append(provider_name)

            if model:
                query += " AND model = ?"
                params.append(model)

            if status_code is not None:
                query += " AND status_code = ?"
                params.append(status_code)
            elif status_min is not None:
                query += " AND status_code >= ?"
                params.append(status_min)

            if date_from:
                query += " AND date(created_at) >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date(created_at) <= ?"
                params.append(date_to)

            cursor.execute(query, params)
            result = cursor.fetchone()

            conn.close()

            return result["count"] if result else 0
        except Exception as e:
            logger.error(f"Failed to get request logs count: {e}")
            return 0

