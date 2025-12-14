import json
import os
import sys
from datetime import datetime
from typing import Optional, List
from models.scraping_job import ScrapingJob
from models.scraping_result import ScrapingResult
from models.category_key import CategoryKey

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class StorageService:
    """Serwis zapisywania i wczytywania danych do/z JSON"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Utwórz folder data/ jeśli nie istnieje
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self._initialized = True
    
    def save_job_to_json(self, job: ScrapingJob) -> str:
        """Zapisuje zadanie do pliku JSON"""
        filename = f"job_{job.job_id}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        # Przygotuj dane do zapisu
        data = {
            "job_id": job.job_id,
            "brand_name": job.brand_name,
            "start_date": job.start_date,
            "end_date": job.end_date,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "scraping_results": [r.to_dict() for r in job.scraping_results],
            "category_key": job.category_key.to_dict() if job.category_key else None,
            "classification_results": job.classification_results,
            "error_message": job.error_message
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return filepath
        except Exception as e:
            raise Exception(f"Błąd zapisywania do JSON: {str(e)}")
    
    def load_job_from_json(self, filepath: str) -> ScrapingJob:
        """Wczytuje zadanie z pliku JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Utwórz ScrapingJob
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
            
            # Wczytaj scraping results
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
            
            # Wczytaj category key
            if data.get("category_key"):
                category_data = data["category_key"]
                job.category_key = CategoryKey(
                    job_id=category_data.get("job_id", job.job_id),
                    categories=category_data.get("categories", []),
                    prompt_type=category_data.get("prompt_type", "ABSA")
                )
                if category_data.get("created_at"):
                    job.category_key.created_at = datetime.fromisoformat(category_data["created_at"])
            
            # Wczytaj classification results
            job.classification_results = data.get("classification_results", {})
            
            return job
            
        except Exception as e:
            raise Exception(f"Błąd wczytywania z JSON: {str(e)}")
    
    def list_saved_jobs(self) -> List[dict]:
        """Zwraca listę zapisanych zadań"""
        jobs = []
        try:
            for filename in os.listdir(self.data_dir):
                if filename.startswith("job_") and filename.endswith(".json"):
                    filepath = os.path.join(self.data_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            jobs.append({
                                "job_id": data.get("job_id"),
                                "brand_name": data.get("brand_name"),
                                "created_at": data.get("created_at"),
                                "results_count": len(data.get("scraping_results", [])),
                                "has_category_key": data.get("category_key") is not None,
                                "filepath": filepath,
                                "filename": filename
                            })
                    except:
                        continue
        except:
            pass
        
        # Sortuj po dacie (najnowsze pierwsze)
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return jobs
    
    def delete_job_json(self, job_id: str) -> bool:
        """Usuwa plik JSON zadania"""
        filename = f"job_{job_id}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except:
            return False

