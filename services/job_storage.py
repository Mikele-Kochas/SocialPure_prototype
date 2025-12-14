import threading
from typing import Dict, Optional
from models.scraping_job import ScrapingJob

class JobStorageService:
    """Serwis przechowywania zadań - in-memory storage"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._jobs: Dict[str, ScrapingJob] = {}
        self._lock = threading.Lock()
        self._initialized = True
    
    def save(self, job: ScrapingJob) -> None:
        """Zapisuje zadanie"""
        with self._lock:
            self._jobs[job.job_id] = job
    
    def get(self, job_id: str) -> Optional[ScrapingJob]:
        """Pobiera zadanie po ID"""
        with self._lock:
            return self._jobs.get(job_id)
    
    def update(self, job: ScrapingJob) -> None:
        """Aktualizuje istniejące zadanie"""
        with self._lock:
            if job.job_id in self._jobs:
                self._jobs[job.job_id] = job
    
    def get_all(self) -> list[ScrapingJob]:
        """Zwraca wszystkie zadania"""
        with self._lock:
            return list(self._jobs.values())
