import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.apify_service import ApifyService
from services.logger import LoggerService

class FacebookSearchService:
    """Serwis wyszukiwania URL-i Facebook przez Google Search"""
    
    def __init__(self):
        self.apify_service = ApifyService()
        self.logger = LoggerService()
    
    def search_facebook_urls(self, query: str, brand_name: str) -> list[str]:
        """Wyszukuje URL-e Facebook dla pojedynczego zapytania"""
        search_query = f"{query} site:facebook.com"
        self.logger.add_log(f"Wyszukuję w Google: {search_query}")
        
        results = self.apify_service.run_google_search(search_query, max_results=20)
        found_urls = []
        
        for item in results:
            # Sprawdź różne struktury danych
            if "organicResults" in item and isinstance(item.get("organicResults"), list):
                for org_result in item.get("organicResults", []):
                    url = org_result.get("url", org_result.get("link", ""))
                    if url and "facebook.com" in url.lower():
                        clean_url = self.clean_url(url)
                        if self.is_valid_facebook_url(clean_url):
                            found_urls.append(clean_url)
            else:
                url = item.get("url", item.get("link", ""))
                if url and "facebook.com" in url.lower():
                    clean_url = self.clean_url(url)
                    if self.is_valid_facebook_url(clean_url):
                        found_urls.append(clean_url)
        
        # Usuń duplikaty
        return list(set(found_urls))
    
    def find_facebook_mentions(self, brand_name: str, search_queries: list[str]) -> dict:
        """Wyszukuje URL-e równolegle dla wielu zapytań"""
        self.logger.add_log(f"Wyszukuję URL-e Facebook dla: {brand_name}")
        
        results_dict = {
            "pages": set(),
            "groups": set(),
            "events": set(),
            "mentions": set()
        }
        
        # Równoległe wyszukiwanie (max 3 równoległe)
        max_workers = min(3, len(search_queries))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.search_facebook_urls, query, brand_name): query
                for query in search_queries[:10]  # Max 10 zapytań
            }
            
            for future in as_completed(futures):
                try:
                    urls = future.result()
                    for url in urls:
                        url_type = self.categorize_url(url)
                        results_dict[url_type].add(url)
                except Exception as e:
                    query = futures[future]
                    self.logger.add_log(f"Błąd dla zapytania '{query}': {str(e)}", "WARNING")
        
        # Konwertuj sety na listy
        return {
            "pages": list(results_dict["pages"]),
            "groups": list(results_dict["groups"]),
            "events": list(results_dict["events"]),
            "mentions": list(results_dict["mentions"])
        }
    
    def categorize_url(self, url: str) -> str:
        """Kategoryzuje URL"""
        url_lower = url.lower()
        if "/groups/" in url_lower:
            return "groups"
        elif "/events/" in url_lower or "/permalink/" in url_lower:
            return "events"
        elif "/posts/" in url_lower:
            return "mentions"
        else:
            return "pages"
    
    def clean_url(self, url: str) -> str:
        """Czyści URL"""
        # Usuń query params i fragmenty
        clean = url.split("?")[0].split("#")[0]
        # Usuń trailing slash
        if clean.endswith("/"):
            clean = clean[:-1]
        return clean
    
    def is_valid_facebook_url(self, url: str) -> bool:
        """Sprawdza czy URL jest prawidłowy"""
        invalid_patterns = ["/login", "/search", "/help", "/about", "/policies", "/media/set"]
        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in invalid_patterns)
