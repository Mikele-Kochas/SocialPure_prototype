from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from .scraping_result import ScrapingResult
from .category_key import CategoryKey

@dataclass
class ScrapingJob:
    """Model danych: główny model zadania scrapingu + klasyfikacji"""
    job_id: str
    brand_name: str
    start_date: str
    end_date: str
    status: str = "pending"  # "pending"/"scraping"/"classifying"/"completed"/"failed"
    current_step: str = ""
    progress: float = 0.0
    scraping_results: List[ScrapingResult] = field(default_factory=list)
    category_key: Optional[CategoryKey] = None
    classification_results: Dict[int, dict] = field(default_factory=dict)  # {index: {category, sentiment}}
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        """Konwersja do słownika"""
        return {
            "job_id": self.job_id,
            "brand_name": self.brand_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "current_step": self.current_step,
            "progress": self.progress,
            "scraping_results_count": len(self.scraping_results),
            "category_key": self.category_key.to_dict() if self.category_key else None,
            "classification_results": self.classification_results,
            "classification_count": len(self.classification_results),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def has_classification(self) -> bool:
        """Sprawdza czy klasyfikacja została wykonana"""
        return len(self.classification_results) > 0
    
    def update_progress(self, step: str, progress: float):
        """Aktualizacja postępu"""
        self.current_step = step
        self.progress = max(0.0, min(1.0, progress))
        self.updated_at = datetime.now()
    
    def get_summary(self) -> dict:
        """Podsumowanie zadania"""
        return {
            "job_id": self.job_id,
            "brand_name": self.brand_name,
            "status": self.status,
            "progress": self.progress,
            "results_count": len(self.scraping_results),
            "categories_count": len(self.category_key.categories) if self.category_key else 0
        }
    
    def is_completed(self) -> bool:
        """Sprawdza czy zakończone"""
        return self.status == "completed"
    
    def get_results_count(self) -> int:
        """Liczba wyników"""
        return len(self.scraping_results)
