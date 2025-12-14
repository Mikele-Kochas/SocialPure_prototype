import sys
import os

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.query_generator import QueryGeneratorService
from services.facebook_search import FacebookSearchService
from services.facebook_scraper import FacebookScraperService
from services.logger import LoggerService
from models.scraping_result import ScrapingResult

class ScrapingOrchestrator:
    """Orchestrator scrapingu - koordynuje proces scrapingu Facebook"""
    
    def __init__(self):
        self.query_generator = QueryGeneratorService()
        self.facebook_search = FacebookSearchService()
        self.facebook_scraper = FacebookScraperService()
        self.logger = LoggerService()
    
    def execute_scraping_job(self, brand_name: str, progress_callback=None) -> list[ScrapingResult]:
        """Główna funkcja scrapingu"""
        try:
            # Krok 1: Generuj zapytania
            if progress_callback:
                progress_callback("Generowanie zapytań wyszukiwania...", 0.1)
            
            queries = self.query_generator.generate_advanced_search_queries(brand_name)
            self.logger.add_log(f"Wygenerowano {len(queries)} zapytań")
            
            # Krok 2: Wyszukaj URL-e
            if progress_callback:
                progress_callback("Wyszukiwanie URL-i Facebook...", 0.2)
            
            urls_dict = self.facebook_search.find_facebook_mentions(brand_name, queries)
            self.logger.add_log(f"Znaleziono: {len(urls_dict['pages'])} stron, "
                              f"{len(urls_dict['groups'])} grup, "
                              f"{len(urls_dict['events'])} wydarzeń, "
                              f"{len(urls_dict['mentions'])} wzmianek")
            
            if not any(urls_dict.values()):
                self.logger.add_log("Nie znaleziono żadnych URL-i", "WARNING")
                return []
            
            # Krok 3: Scrapuj posty (priorytetyzacja)
            all_results = []
            
            # Najpierw wzmianki (najbardziej istotne)
            if urls_dict["mentions"]:
                if progress_callback:
                    progress_callback("Pobieranie postów ze wzmianek...", 0.3)
                results = self.facebook_scraper.scrape_urls_parallel(
                    urls_dict["mentions"][:10], "post", max_posts_per_url=1
                )
                all_results.extend(self._convert_to_results(results))
            
            # Grupy
            if urls_dict["groups"]:
                if progress_callback:
                    progress_callback("Pobieranie postów z grup...", 0.5)
                results = self.facebook_scraper.scrape_urls_parallel(
                    urls_dict["groups"][:5], "group", max_posts_per_url=15
                )
                all_results.extend(self._convert_to_results(results))
            
            # Wydarzenia
            if urls_dict["events"]:
                if progress_callback:
                    progress_callback("Pobieranie postów z wydarzeń...", 0.7)
                results = self.facebook_scraper.scrape_urls_parallel(
                    urls_dict["events"][:5], "event", max_posts_per_url=10
                )
                all_results.extend(self._convert_to_results(results))
            
            # Strony
            if urls_dict["pages"]:
                if progress_callback:
                    progress_callback("Pobieranie postów ze stron...", 0.8)
                results = self.facebook_scraper.scrape_urls_parallel(
                    urls_dict["pages"][:5], "page", max_posts_per_url=10
                )
                all_results.extend(self._convert_to_results(results))
            
            # Usuń duplikaty
            unique_results = self._remove_duplicates_by_url(all_results)
            self.logger.add_log(f"Zebrano {len(unique_results)} unikalnych wyników")
            
            return unique_results
            
        except Exception as e:
            self.logger.add_log(f"Błąd scrapingu: {str(e)}", "ERROR")
            raise
    
    def _convert_to_results(self, apify_items: list[dict]) -> list[ScrapingResult]:
        """Konwertuje raw wyniki Apify do ScrapingResult"""
        return [ScrapingResult.from_apify_item(item) for item in apify_items]
    
    def _remove_duplicates_by_url(self, results: list[ScrapingResult]) -> list[ScrapingResult]:
        """Usuwa duplikaty po URL"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result.url and result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        return unique_results
