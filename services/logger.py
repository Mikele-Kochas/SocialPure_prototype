import threading
from datetime import datetime
from typing import List

class LoggerService:
    """Thread-safe system logowania"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._logs: List[str] = []
        self._logs_lock = threading.Lock()
        self._max_logs = 1000
        self._initialized = True
    
    def add_log(self, message: str, level: str = "INFO"):
        """Dodaj log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        with self._logs_lock:
            self._logs.append(log_entry)
            # Ogranicz liczbę logów
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]
        
        return log_entry
    
    def get_logs(self) -> List[str]:
        """Pobierz wszystkie logi"""
        with self._logs_lock:
            return self._logs.copy()
    
    def clear_logs(self):
        """Wyczyść logi"""
        with self._logs_lock:
            self._logs.clear()
    
    def get_logs_by_level(self, level: str) -> List[str]:
        """Filtruj po poziomie"""
        with self._logs_lock:
            return [log for log in self._logs if f"[{level}]" in log]
