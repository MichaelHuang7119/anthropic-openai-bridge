"""
高并发场景下的多层隔离机制
为高并发环境提供更强健的并发控制和消息隔离
"""
import asyncio
import logging
from typing import Dict, Optional, Tuple
import time
import uuid

logger = logging.getLogger(__name__)


class ConcurrencyManager:
    """
    高并发场景下的多层隔离管理器

    隔离层级：
    1. API Key 级别 - 防止多用户共享API key时的阻塞
    2. Session 级别 - 防止会话间串扰
    3. Chat 级别 - 防止对话间串扰
    4. Message 级别 - 防止消息间串扰
    5. Model 级别 - 防止模型间串扰
    6. Provider 级别 - 防止提供商间串扰
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 多维度信号量存储
        self._api_key_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._session_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._chat_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._message_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._model_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._provider_semaphores: Dict[str, asyncio.Semaphore] = {}

        # 锁
        self._semaphore_lock = asyncio.Lock()

        # 活跃请求跟踪
        self._active_requests: Dict[str, dict] = {}
        self._request_lock = asyncio.Lock()

        # 配置限制
        self._limits = {
            # API Key 限制（按提供商）
            "api_key_limits": {
                "anthropic": 3,    # 严格限制
                "openai": 5,
                "modelscope": 8,
                "azure": 4,
                "default": 5
            },
            # Session 限制
            "session_limit": 2,
            # Chat 限制（严格：每个对话1个）
            "chat_limit": 1,
            # Message 限制（最严格：每个消息1个）
            "message_limit": 1,
            # Model 限制
            "model_limit": 2,
            # Provider 限制
            "provider_limit": 10
        }

    async def acquire_multi_level_semaphore(
        self,
        api_key: str,
        provider_name: str,
        session_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        message_id: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Tuple[asyncio.Semaphore, ...]:
        """
        获取多层级信号量

        Args:
            api_key: API密钥
            provider_name: 提供商名称
            session_id: 会话ID（可选）
            chat_id: 对话ID（可选）
            message_id: 消息ID（可选）
            model_name: 模型名称（可选）

        Returns:
            多层级信号量元组
        """
        async with self._semaphore_lock:
            # 1. API Key 级别
            api_key_id = self._get_api_key_id(api_key)
            if api_key_id not in self._api_key_semaphores:
                limit = self._limits["api_key_limits"].get(provider_name.lower(), self._limits["api_key_limits"]["default"])
                self._api_key_semaphores[api_key_id] = asyncio.Semaphore(limit)
            api_key_sem = self._api_key_semaphores[api_key_id]

            # 2. Provider 级别
            provider_sem = None
            if provider_name not in self._provider_semaphores:
                self._provider_semaphores[provider_name] = asyncio.Semaphore(self._limits["provider_limit"])
            provider_sem = self._provider_semaphores[provider_name]

            # 3. Session 级别
            session_sem = None
            if session_id and session_id not in self._session_semaphores:
                self._session_semaphores[session_id] = asyncio.Semaphore(self._limits["session_limit"])
            session_sem = self._session_semaphores.get(session_id)

            # 4. Chat 级别
            chat_sem = None
            if chat_id and chat_id not in self._chat_semaphores:
                self._chat_semaphores[chat_id] = asyncio.Semaphore(self._limits["chat_limit"])
            chat_sem = self._chat_semaphores.get(chat_id)

            # 5. Message 级别
            message_sem = None
            if message_id and message_id not in self._message_semaphores:
                self._message_semaphores[message_id] = asyncio.Semaphore(self._limits["message_limit"])
            message_sem = self._message_semaphores.get(message_id)

            # 6. Model 级别
            model_sem = None
            if model_name and model_name not in self._model_semaphores:
                self._model_semaphores[model_name] = asyncio.Semaphore(self._limits["model_limit"])
            model_sem = self._model_semaphores.get(model_name)

        # 按优先级获取锁：message > chat > session > api_key > provider > model
        start_time = time.time()
        timeout = 30

        acquired_sems = []
        try:
            # 获取 API Key 信号量（必须）
            await self._acquire_with_timeout(api_key_sem, "api_key", timeout)
            acquired_sems.append(api_key_sem)

            # 获取 Provider 信号量（必须）
            await self._acquire_with_timeout(provider_sem, "provider", timeout)
            acquired_sems.append(provider_sem)

            # 获取可选信号量
            if session_sem:
                await self._acquire_with_timeout(session_sem, "session", timeout)
                acquired_sems.append(session_sem)
            else:
                acquired_sems.append(None)

            if chat_sem:
                await self._acquire_with_timeout(chat_sem, "chat", timeout)
                acquired_sems.append(chat_sem)
            else:
                acquired_sems.append(None)

            if message_sem:
                await self._acquire_with_timeout(message_sem, "message", timeout)
                acquired_sems.append(message_sem)
            else:
                acquired_sems.append(None)

            if model_sem:
                await self._acquire_with_timeout(model_sem, "model", timeout)
                acquired_sems.append(model_sem)
            else:
                acquired_sems.append(None)

            return tuple(acquired_sems)

        except Exception as e:
            # 清理已获取的信号量
            for sem in acquired_sems:
                if sem:
                    sem.release()
            raise e

    async def release_multi_level_semaphore(
        self,
        api_key: str,
        provider_name: str,
        session_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        message_id: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """释放多层级信号量"""
        api_key_id = self._get_api_key_id(api_key)

        # 释放所有层级的信号量
        if api_key_id in self._api_key_semaphores:
            self._api_key_semaphores[api_key_id].release()

        if provider_name in self._provider_semaphores:
            self._provider_semaphores[provider_name].release()

        if session_id and session_id in self._session_semaphores:
            self._session_semaphores[session_id].release()

        if chat_id and chat_id in self._chat_semaphores:
            self._chat_semaphores[chat_id].release()

        if message_id and message_id in self._message_semaphores:
            self._message_semaphores[message_id].release()

        if model_name and model_name in self._model_semaphores:
            self._model_semaphores[model_name].release()

    async def _acquire_with_timeout(self, semaphore: asyncio.Semaphore, name: str, timeout: int):
        """带超时的信号量获取"""
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
            logger.debug(f"Acquired {name} semaphore")
        except asyncio.TimeoutError:
            logger.error(f"Timeout acquiring {name} semaphore")
            raise

    def _get_api_key_id(self, api_key: str) -> str:
        """生成API key的简短标识"""
        if len(api_key) < 12:
            return f"key_{hash(api_key) % 10000:04d}"
        return f"{api_key[:8]}_..._{api_key[-4:]}"

    async def register_request(self, request_id: str, context: dict):
        """注册活跃请求"""
        async with self._request_lock:
            self._active_requests[request_id] = {
                **context,
                "start_time": time.time(),
                "status": "active"
            }

    async def unregister_request(self, request_id: str):
        """注销活跃请求"""
        async with self._request_lock:
            if request_id in self._active_requests:
                self._active_requests[request_id]["status"] = "completed"
                self._active_requests[request_id]["end_time"] = time.time()

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "api_key_semaphores": len(self._api_key_semaphores),
            "session_semaphores": len(self._session_semaphores),
            "chat_semaphores": len(self._chat_semaphores),
            "message_semaphores": len(self._message_semaphores),
            "model_semaphores": len(self._model_semaphores),
            "provider_semaphores": len(self._provider_semaphores),
            "active_requests": len(self._active_requests),
            "limits": self._limits
        }


# 全局实例
concurrency_manager = ConcurrencyManager()


class ConcurrencyGuard:
    """并发控制上下文管理器"""

    def __init__(
        self,
        api_key: str,
        provider_name: str,
        session_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        message_id: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key
        self.provider_name = provider_name
        self.session_id = session_id
        self.chat_id = chat_id
        self.message_id = message_id
        self.model_name = model_name
        self.request_id = str(uuid.uuid4())

    async def __aenter__(self):
        # 注册活跃请求
        await concurrency_manager.register_request(
            self.request_id,
            {
                "api_key": self.api_key[:12] + "...",
                "provider": self.provider_name,
                "session_id": self.session_id,
                "chat_id": self.chat_id,
                "message_id": self.message_id,
                "model_name": self.model_name
            }
        )

        # 获取多层级信号量
        self.semaphores = await concurrency_manager.acquire_multi_level_semaphore(
            self.api_key,
            self.provider_name,
            self.session_id,
            self.chat_id,
            self.message_id,
            self.model_name
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            # 释放信号量
            await concurrency_manager.release_multi_level_semaphore(
                self.api_key,
                self.provider_name,
                self.session_id,
                self.chat_id,
                self.message_id,
                self.model_name
            )
        finally:
            # 注销活跃请求
            await concurrency_manager.unregister_request(self.request_id)