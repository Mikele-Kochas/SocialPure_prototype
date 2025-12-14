"""
Skrypt migracji danych z JSON do SQLite
Uruchom: python scripts/migrate_json_to_sqlite.py
"""
import sys
import os
import json
from datetime import datetime

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database_service import DatabaseService
from models.scraping_job import ScrapingJob
from models.scraping_result import ScrapingResult
from models.category_key import CategoryKey

def migrate_json_to_sqlite():
    """Migruje wszystkie pliki JSON do SQLite"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    db = DatabaseService()
    
    migrated_count = 0
    error_count = 0
    
    print("Rozpoczynam migrację danych z JSON do SQLite...")
    print(f"Katalog danych: {data_dir}")
    print("-" * 50)
    
    # Znajdź wszystkie pliki JSON
    json_files = []
    for filename in os.listdir(data_dir):
        if filename.startswith("job_") and filename.endswith(".json"):
            json_files.append(os.path.join(data_dir, filename))
    
    if not json_files:
        print("Nie znaleziono plików JSON do migracji.")
        return
    
    print(f"Znaleziono {len(json_files)} plików JSON do migracji.\n")
    
    for filepath in json_files:
        try:
            print(f"Migruję: {os.path.basename(filepath)}")
            
            # Wczytaj JSON
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Sprawdź czy zadanie już istnieje w bazie
            existing_job = db.load_job(data["job_id"])
            if existing_job:
                print(f"  ⚠️  Zadanie {data['job_id']} już istnieje w bazie. Pomijam.")
                continue
            
            # Utwórz obiekt ScrapingJob
            job = ScrapingJob(
                job_id=data["job_id"],
                brand_name=data["brand_name"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                status=data.get("status", "completed"),
                current_step=data.get("current_step", ""),
                progress=data.get("progress", 0.0),
                error_message=data.get("error_message")
            )
            
            job.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
            job.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
            
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
            
            # Zapisz do SQLite
            db.save_job(job)
            
            print(f"  ✅ Zapisano: {len(job.scraping_results)} wyników scrapingu, "
                  f"{len(job.classification_results)} klasyfikacji")
            migrated_count += 1
            
        except Exception as e:
            print(f"  ❌ Błąd migracji {os.path.basename(filepath)}: {str(e)}")
            error_count += 1
    
    print("-" * 50)
    print(f"\nMigracja zakończona!")
    print(f"  ✅ Zmigrowano: {migrated_count} zadań")
    print(f"  ❌ Błędy: {error_count}")
    print(f"\nBaza danych SQLite: {db.db_path}")
    print("\nUwaga: Pliki JSON nie zostały usunięte. Możesz je usunąć ręcznie po weryfikacji.")

if __name__ == "__main__":
    migrate_json_to_sqlite()

