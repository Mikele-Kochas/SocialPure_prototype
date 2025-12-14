"""
Serwis bazy danych SQLite - zarządzanie połączeniem i schematem
"""
import sqlite3
import json
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DatabaseService:
    """Serwis zarządzania bazą danych SQLite"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Ścieżka do bazy danych
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, 'socialpure.db')
        
        # Inicjalizuj schemat
        self._init_schema()
        
        self._initialized = True
    
    @contextmanager
    def get_connection(self):
        """Context manager dla połączenia z bazą danych"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Umożliwia dostęp przez nazwy kolumn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """Inicjalizuje schemat bazy danych"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela jobs - główne dane zadania
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    brand_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    current_step TEXT DEFAULT '',
                    progress REAL DEFAULT 0.0,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Tabela scraping_results - wyniki scrapingu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraping_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    url TEXT,
                    author TEXT,
                    date TEXT,
                    source_type TEXT DEFAULT 'post',
                    platform TEXT DEFAULT 'facebook',
                    metadata TEXT,  -- JSON string
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
                )
            """)
            
            # Tabela category_keys - klucze kategorii
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS category_keys (
                    job_id TEXT PRIMARY KEY,
                    prompt_type TEXT DEFAULT 'ABSA',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
                )
            """)
            
            # Tabela categories - kategorie (aspekty)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    aspekt TEXT NOT NULL,
                    definicja TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES category_keys(job_id) ON DELETE CASCADE
                )
            """)
            
            # Tabela classification_results - wyniki klasyfikacji
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classification_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    comment_index INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    classified_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
                    UNIQUE(job_id, comment_index)
                )
            """)
            
            # Indeksy dla lepszej wydajności
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scraping_results_job_id ON scraping_results(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_job_id ON categories(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_classification_results_job_id ON classification_results(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
            
            conn.commit()
    
    def execute_query(self, query: str, params: tuple = ()):
        """Wykonuje zapytanie i zwraca wyniki"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()):
        """Wykonuje zapytanie UPDATE/INSERT/DELETE"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount
    
    # ========== Metody CRUD dla ScrapingJob ==========
    
    def save_job(self, job) -> None:
        """Zapisuje zadanie do bazy danych"""
        from models.scraping_job import ScrapingJob
        from models.scraping_result import ScrapingResult
        from models.category_key import CategoryKey
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Zapisz główne dane zadania
            cursor.execute("""
                INSERT OR REPLACE INTO jobs 
                (job_id, brand_name, start_date, end_date, status, current_step, 
                 progress, error_message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id,
                job.brand_name,
                job.start_date,
                job.end_date,
                job.status,
                job.current_step,
                job.progress,
                job.error_message,
                job.created_at.isoformat(),
                job.updated_at.isoformat()
            ))
            
            # Usuń stare wyniki scrapingu
            cursor.execute("DELETE FROM scraping_results WHERE job_id = ?", (job.job_id,))
            
            # Zapisz wyniki scrapingu
            for idx, result in enumerate(job.scraping_results):
                cursor.execute("""
                    INSERT INTO scraping_results 
                    (job_id, text, url, author, date, source_type, platform, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id,
                    result.text,
                    result.url,
                    result.author,
                    result.date.isoformat() if result.date else None,
                    result.source_type,
                    result.platform,
                    json.dumps(result.metadata) if result.metadata else None
                ))
            
            # Zapisz category_key jeśli istnieje
            if job.category_key:
                cursor.execute("""
                    INSERT OR REPLACE INTO category_keys (job_id, prompt_type, created_at)
                    VALUES (?, ?, ?)
                """, (
                    job.category_key.job_id,
                    job.category_key.prompt_type,
                    job.category_key.created_at.isoformat()
                ))
                
                # Usuń stare kategorie
                cursor.execute("DELETE FROM categories WHERE job_id = ?", (job.job_id,))
                
                # Zapisz kategorie
                for cat in job.category_key.categories:
                    cursor.execute("""
                        INSERT INTO categories (job_id, aspekt, definicja)
                        VALUES (?, ?, ?)
                    """, (
                        job.job_id,
                        cat.get('aspekt', ''),
                        cat.get('definicja', '')
                    ))
            
            # Zapisz classification_results
            cursor.execute("DELETE FROM classification_results WHERE job_id = ?", (job.job_id,))
            
            for idx, class_result in job.classification_results.items():
                cursor.execute("""
                    INSERT INTO classification_results 
                    (job_id, comment_index, category, sentiment, classified_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    job.job_id,
                    int(idx),
                    class_result.get('category', ''),
                    class_result.get('sentiment', 'neutralny'),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
    
    def load_job(self, job_id: str):
        """Wczytuje zadanie z bazy danych"""
        from models.scraping_job import ScrapingJob
        from models.scraping_result import ScrapingResult
        from models.category_key import CategoryKey
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Wczytaj główne dane zadania
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            job_row = cursor.fetchone()
            
            if not job_row:
                return None
            
            # Utwórz obiekt ScrapingJob
            job = ScrapingJob(
                job_id=job_row['job_id'],
                brand_name=job_row['brand_name'],
                start_date=job_row['start_date'],
                end_date=job_row['end_date'],
                status=job_row['status'],
                current_step=job_row['current_step'] or '',
                progress=job_row['progress'] or 0.0,
                error_message=job_row['error_message']
            )
            job.created_at = datetime.fromisoformat(job_row['created_at'])
            job.updated_at = datetime.fromisoformat(job_row['updated_at'])
            
            # Wczytaj scraping_results
            cursor.execute("SELECT * FROM scraping_results WHERE job_id = ? ORDER BY id", (job_id,))
            for row in cursor.fetchall():
                result = ScrapingResult(
                    text=row['text'],
                    url=row['url'] or '',
                    author=row['author'] or '',
                    date=datetime.fromisoformat(row['date']) if row['date'] else None,
                    source_type=row['source_type'] or 'post',
                    platform=row['platform'] or 'facebook',
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                job.scraping_results.append(result)
            
            # Wczytaj category_key
            cursor.execute("SELECT * FROM category_keys WHERE job_id = ?", (job_id,))
            category_key_row = cursor.fetchone()
            
            if category_key_row:
                cursor.execute("SELECT * FROM categories WHERE job_id = ?", (job_id,))
                categories = []
                for cat_row in cursor.fetchall():
                    categories.append({
                        'aspekt': cat_row['aspekt'],
                        'definicja': cat_row['definicja']
                    })
                
                job.category_key = CategoryKey(
                    job_id=job_id,
                    categories=categories,
                    prompt_type=category_key_row['prompt_type']
                )
                job.category_key.created_at = datetime.fromisoformat(category_key_row['created_at'])
            
            # Wczytaj classification_results
            cursor.execute("SELECT * FROM classification_results WHERE job_id = ?", (job_id,))
            job.classification_results = {}
            for row in cursor.fetchall():
                job.classification_results[row['comment_index']] = {
                    'category': row['category'],
                    'sentiment': row['sentiment']
                }
            
            return job
    
    def get_all_jobs(self, status: Optional[str] = None) -> List:
        """Zwraca wszystkie zadania, opcjonalnie filtrowane po statusie"""
        from models.scraping_job import ScrapingJob
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute("SELECT job_id FROM jobs WHERE status = ? ORDER BY created_at DESC", (status,))
            else:
                cursor.execute("SELECT job_id FROM jobs ORDER BY created_at DESC")
            
            job_ids = [row['job_id'] for row in cursor.fetchall()]
            return [self.load_job(job_id) for job_id in job_ids]
    
    def delete_job(self, job_id: str) -> bool:
        """Usuwa zadanie z bazy danych (CASCADE usunie powiązane rekordy)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            return cursor.rowcount > 0
    
    def list_jobs_summary(self) -> List[Dict]:
        """Zwraca podsumowanie wszystkich zadań"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    j.job_id,
                    j.brand_name,
                    j.status,
                    j.created_at,
                    COUNT(sr.id) as results_count,
                    CASE WHEN ck.job_id IS NOT NULL THEN 1 ELSE 0 END as has_category_key
                FROM jobs j
                LEFT JOIN scraping_results sr ON j.job_id = sr.job_id
                LEFT JOIN category_keys ck ON j.job_id = ck.job_id
                GROUP BY j.job_id
                ORDER BY j.created_at DESC
            """)
            
            return [
                {
                    'job_id': row['job_id'],
                    'brand_name': row['brand_name'],
                    'status': row['status'],
                    'created_at': row['created_at'],
                    'results_count': row['results_count'],
                    'has_category_key': bool(row['has_category_key'])
                }
                for row in cursor.fetchall()
            ]

