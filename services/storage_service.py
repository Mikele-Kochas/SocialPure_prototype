import os
import sys
import json
from datetime import datetime
from typing import Optional, List
from models.scraping_job import ScrapingJob
from models.scraping_result import ScrapingResult
from models.category_key import CategoryKey

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.database_service import DatabaseService

class StorageService:
    """Serwis zapisywania i wczytywania danych - używa SQLite"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Utwórz folder data/ jeśli nie istnieje (dla raportów, etc.)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.db = DatabaseService()
        
        self._initialized = True
    
    def save_job_to_json(self, job: ScrapingJob) -> str:
        """Zapisuje zadanie do bazy danych SQLite (zachowana kompatybilność API)"""
        self.db.save_job(job)
        # Zwróć ścieżkę do bazy danych dla kompatybilności
        return self.db.db_path
    
    def load_job_from_json(self, filepath: str) -> ScrapingJob:
        """Wczytuje zadanie z bazy danych SQLite lub JSON (fallback dla migracji)"""
        # Jeśli filepath to ścieżka do JSON (stara wersja), spróbuj wczytać z JSON
        if filepath.endswith('.json') and os.path.exists(filepath):
            # Fallback do starego formatu JSON (dla migracji)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                job = ScrapingJob(
                    job_id=data["job_id"],
                    brand_name=data["brand_name"],
                    start_date=data["start_date"],
                    end_date=data["end_date"],
                    status=data.get("status", "completed")
                )
                
                job.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
                job.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
                job.error_message = data.get("error_message")
                
                job.scraping_results = []
                for result_data in data.get("scraping_results", []):
                    result = ScrapingResult(
                        text=result_data.get("text", ""),
                        url=result_data.get("url", ""),
                        author=result_data.get("author", ""),
                        date=datetime.fromisoformat(result_data["date"]) if result_data.get("date") else None,
                        source_type=result_data.get("source_type", "post"),
                        platform=result_data.get("platform", "facebook"),
                        metadata=result_data.get("metadata", {})
                    )
                    job.scraping_results.append(result)
                
                if data.get("category_key"):
                    category_data = data["category_key"]
                    job.category_key = CategoryKey(
                        job_id=category_data.get("job_id", job.job_id),
                        categories=category_data.get("categories", []),
                        prompt_type=category_data.get("prompt_type", "ABSA")
                    )
                    if category_data.get("created_at"):
                        job.category_key.created_at = datetime.fromisoformat(category_data["created_at"])
                
                job.classification_results = data.get("classification_results", {})
                
                # Zapisz do SQLite i zwróć
                self.db.save_job(job)
                return job
            except Exception as e:
                # Jeśli nie udało się wczytać z JSON, spróbuj z bazy
                pass
        
        # Wczytaj z bazy po job_id z filepath
        job_id = os.path.basename(filepath).replace('job_', '').replace('.json', '')
        job = self.db.load_job(job_id)
        if job:
            return job
        
        raise Exception(f"Nie znaleziono zadania: {job_id}")
    
    def list_saved_jobs(self) -> List[dict]:
        """Zwraca listę zapisanych zadań z bazy danych"""
        jobs_summary = self.db.list_jobs_summary()
        
        # Przekształć do formatu kompatybilnego ze starą wersją
        return [
            {
                "job_id": job['job_id'],
                "brand_name": job['brand_name'],
                "created_at": job['created_at'],
                "results_count": job['results_count'],
                "has_category_key": job['has_category_key'],
                "filepath": f"job_{job['job_id']}.json",  # Dla kompatybilności
                "filename": f"job_{job['job_id']}.json"
            }
            for job in jobs_summary
        ]
    
    def delete_job_json(self, job_id: str) -> bool:
        """Usuwa zadanie z bazy danych"""
        return self.db.delete_job(job_id)
