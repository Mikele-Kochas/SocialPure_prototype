import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.apify_service import ApifyService
from services.logger import LoggerService
from models.scraping_result import ScrapingResult

class FacebookScraperService:
    """Serwis scrapingu postów z Facebook"""
    
    def __init__(self):
        self.apify_service = ApifyService()
        self.logger = LoggerService()
    
    def scrape_single_url(self, url: str, url_type: str, max_posts: int = 20) -> list[dict]:
        """Scrapuje posty z pojedynczego URL"""
        self.logger.add_log(f"Scrapuję {url_type}: {url}")
        
        try:
            results = self.apify_service.run_facebook_scraper([url], max_posts)
            filtered = self.filter_results(results)
            return filtered
        except Exception as e:
            self.logger.add_log(f"Błąd scrapingu {url}: {str(e)}", "ERROR")
            return []
    
    def scrape_urls_parallel(self, urls: list[str], url_type: str, max_posts_per_url: int = 20) -> list[dict]:
        """Scrapuje wiele URL-i równolegle"""
        if not urls:
            return []
        
        self.logger.add_log(f"Scrapuję {len(urls)} {url_type}(ów) równolegle")
        
        all_results = []
        max_workers = min(2, len(urls))  # Max 2 równoległe (limit pamięci Apify)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.scrape_single_url, url, url_type, max_posts_per_url): url
                for url in urls
            }
            
            for future in as_completed(futures):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    url = futures[future]
                    self.logger.add_log(f"Błąd dla {url}: {str(e)}", "WARNING")
        
        # Usuń duplikaty
        return self.remove_duplicates(all_results)
    
    def filter_results(self, items: list[dict]) -> list[dict]:
        """Filtruje wyniki scrapingu"""
        filtered = []
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # Sprawdź błędy
            if "error" in item:
                continue
            
            # Sprawdź tekst
            text = self.extract_post_text(item)
            if not text or len(text.strip()) < 5:
                continue
            
            # Sprawdź komunikaty o blokadzie
            text_lower = text.lower()
            if "page access was blocked" in text_lower or "page is not available" in text_lower:
                continue
            
            filtered.append(item)
        
        return filtered
    
    def extract_post_text(self, item: dict) -> str:
        """Wyciąga tekst posta z różnych pól Apify"""
        return item.get("text") or item.get("postText") or item.get("message") or ""
    
    def remove_duplicates(self, results: list[dict]) -> list[dict]:
        """Usuwa duplikaty po URL"""
        seen_urls = set()
        unique_results = []
        
        for item in results:
            url = item.get("url") or item.get("postUrl") or ""
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(item)
        
        return unique_results
