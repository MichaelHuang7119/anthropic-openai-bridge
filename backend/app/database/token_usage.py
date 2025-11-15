"""Token usage database operations."""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TokenUsageManager:
    """Manages token usage statistics in the database."""

    def __init__(self, db_core):
        """
        Initialize token usage manager.

        Args:
            db_core: DatabaseCore instance for connection management.
        """
        self.db_core = db_core

    async def update_token_usage(
        self,
        date: str,
        provider_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_estimate: float
    ):
        """Update token usage statistics."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            # Try to update existing record
            cursor.execute("""
                UPDATE token_usage
                SET request_count = request_count + 1,
                    total_input_tokens = total_input_tokens + ?,
                    total_output_tokens = total_output_tokens + ?,
                    total_cost_estimate = total_cost_estimate + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE date = ? AND provider_name = ? AND model = ?
            """, (input_tokens, output_tokens, cost_estimate, date, provider_name, model))

            # If no rows were updated, insert new record
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO token_usage (
                        date, provider_name, model, request_count,
                        total_input_tokens, total_output_tokens, total_cost_estimate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (date, provider_name, model, 1, input_tokens, output_tokens, cost_estimate))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update token usage: {e}")

    async def get_token_usage_summary(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get token usage summary."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM token_usage WHERE 1=1"
            params = []

            if date_from:
                query += " AND date >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date <= ?"
                params.append(date_to)

            query += " ORDER BY date DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            return {
                "summary": [dict(row) for row in rows],
                "total_requests": sum(row["request_count"] for row in rows),
                "total_input_tokens": sum(row["total_input_tokens"] for row in rows),
                "total_output_tokens": sum(row["total_output_tokens"] for row in rows),
                "total_cost_estimate": sum(row["total_cost_estimate"] for row in rows)
            }
        except Exception as e:
            logger.error(f"Failed to get token usage summary: {e}")
            return {"summary": [], "total_requests": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_cost_estimate": 0}

