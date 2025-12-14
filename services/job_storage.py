import threading
from typing import Dict, Optional
from models.scraping_job import ScrapingJob
from services.database_service import DatabaseService

class JobStorageService:
    """Serwis przechowywania zadań - używa SQLite"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db = DatabaseService()
        self._cache: Dict[str, ScrapingJob] = {}  # Cache dla szybkiego dostępu
        self._lock = threading.Lock()
        self._initialized = True
    
    def save(self, job: ScrapingJob) -> None:
        """Zapisuje zadanie do bazy danych i cache"""
        with self._lock:
            self.db.save_job(job)
            self._cache[job.job_id] = job
    
    def get(self, job_id: str) -> Optional[ScrapingJob]:
        """Pobiera zadanie po ID (najpierw z cache, potem z bazy)"""
        with self._lock:
            # Sprawdź cache
            if job_id in self._cache:
                return self._cache[job_id]
            
            # Wczytaj z bazy
            job = self.db.load_job(job_id)
            if job:
                self._cache[job_id] = job
            return job
    
    def update(self, job: ScrapingJob) -> None:
        """Aktualizuje istniejące zadanie"""
        with self._lock:
            self.db.save_job(job)  # INSERT OR REPLACE
            self._cache[job.job_id] = job
    
    def get_all(self) -> list[ScrapingJob]:
        """Zwraca wszystkie zadania z bazy danych"""
        with self._lock:
            jobs = self.db.get_all_jobs()
            # Zaktualizuj cache
            for job in jobs:
                self._cache[job.job_id] = job
            return jobs
    
    def clear_cache(self):
        """Czyści cache (użyteczne po długim czasie)"""
        with self._lock:
            self._cache.clear()
