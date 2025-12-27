"""配置热更新模块 - 监听配置文件变化并自动重新加载"""
import logging
import threading
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

# 尝试导入 watchdog，如果不可用则使用轮询方式
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # 创建虚拟基类
    class FileSystemEventHandler:
        pass
    logger.warning("watchdog not available, using polling mode for config hot reload")


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件变化处理器"""
    
    def __init__(self, config_path: str, reload_callback: Callable[[], None]):
        """
        初始化文件处理器
        
        Args:
            config_path: 配置文件路径
            reload_callback: 重新加载配置的回调函数
        """
        self.config_path = Path(config_path).resolve()
        self.reload_callback = reload_callback
        self.last_modified = self._get_file_mtime()
        self._reload_lock = threading.Lock()
        self._last_reload_time = None
        
    def _get_file_mtime(self) -> Optional[float]:
        """获取文件修改时间"""
        try:
            return self.config_path.stat().st_mtime
        except (OSError, FileNotFoundError):
            return None
    
    def _should_reload(self) -> bool:
        """检查是否应该重新加载配置"""
        current_mtime = self._get_file_mtime()
        if current_mtime is None:
            return False
        
        # 防止频繁重新加载（至少间隔 1 秒）
        if self._last_reload_time:
            time_since_last_reload = datetime.now().timestamp() - self._last_reload_time
            if time_since_last_reload < 1.0:
                return False
        
        if current_mtime != self.last_modified:
            self.last_modified = current_mtime
            return True
        return False
    
    def _reload_config(self):
        """重新加载配置"""
        with self._reload_lock:
            if not self._should_reload():
                return
            
            try:
                logger.info(f"Configuration file changed, reloading: {self.config_path}")
                self.reload_callback()
                self._last_reload_time = datetime.now().timestamp()
                logger.info("Configuration reloaded successfully")
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}", exc_info=True)
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        # 只处理目标配置文件
        if Path(event.src_path).resolve() == self.config_path:
            self._reload_config()


class ConfigHotReloader:
    """配置热更新管理器"""
    
    def __init__(self, config_path: str, reload_callback: Callable[[], None], poll_interval: float = 2.0):
        """
        初始化配置热更新管理器
        
        Args:
            config_path: 配置文件路径
            reload_callback: 重新加载配置的回调函数
            poll_interval: 轮询间隔（秒），仅在 watchdog 不可用时使用
        """
        self.config_path = Path(config_path).resolve()
        self.reload_callback = reload_callback
        self.poll_interval = poll_interval
        self.observer: Optional[Observer] = None
        self.polling_thread: Optional[threading.Thread] = None
        self._running = False
        self._handler: Optional[ConfigFileHandler] = None
    
    def start(self):
        """启动配置热更新监听"""
        if not self.config_path.exists():
            logger.warning(f"Configuration file not found: {self.config_path}, hot reload disabled")
            return
        
        self._running = True
        
        if WATCHDOG_AVAILABLE:
            self._start_watchdog()
        else:
            self._start_polling()
        
        logger.info(f"Configuration hot reload enabled for: {self.config_path}")
    
    def _start_watchdog(self):
        """使用 watchdog 启动文件监听"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog not available, falling back to polling mode")
            self._start_polling()
            return

        try:
            self._handler = ConfigFileHandler(str(self.config_path), self.reload_callback)
            self.observer = Observer()

            # 监听配置文件所在目录
            watch_dir = self.config_path.parent
            self.observer.schedule(self._handler, str(watch_dir), recursive=False)
            self.observer.start()

            logger.info(f"Using watchdog for config hot reload (watching: {watch_dir})")
        except Exception as e:
            logger.error(f"Failed to start watchdog observer: {e}")
            logger.info("Falling back to polling mode")
            self._start_polling()
    
    def _start_polling(self):
        """使用轮询方式检查文件变化"""
        def poll_loop():
            import time
            handler = ConfigFileHandler(str(self.config_path), self.reload_callback)
            while self._running:
                try:
                    handler._reload_config()
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                finally:
                    time.sleep(self.poll_interval)
        
        self.polling_thread = threading.Thread(target=poll_loop, daemon=True)
        self.polling_thread.start()
        logger.info(f"Using polling mode for config hot reload (interval: {self.poll_interval}s)")
    
    def stop(self):
        """停止配置热更新监听"""
        self._running = False
        
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=2)
            except Exception as e:
                logger.error(f"Error stopping observer: {e}")
        
        if self.polling_thread:
            self.polling_thread.join(timeout=2)
        
        logger.info("Configuration hot reload stopped")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        if self.observer:
            return self.observer.is_alive()
        if self.polling_thread:
            return self.polling_thread.is_alive()
        return False


# 全局热更新管理器实例
_hot_reloader: Optional[ConfigHotReloader] = None


def start_config_hot_reload(config_path: str, reload_callback: Callable[[], None], poll_interval: float = 2.0):
    """
    启动配置热更新
    
    Args:
        config_path: 配置文件路径
        reload_callback: 重新加载配置的回调函数
        poll_interval: 轮询间隔（秒）
    """
    global _hot_reloader
    
    if _hot_reloader:
        logger.warning("Config hot reload already started")
        return
    
    _hot_reloader = ConfigHotReloader(config_path, reload_callback, poll_interval)
    _hot_reloader.start()


def stop_config_hot_reload():
    """停止配置热更新"""
    global _hot_reloader
    
    if _hot_reloader:
        _hot_reloader.stop()
        _hot_reloader = None

