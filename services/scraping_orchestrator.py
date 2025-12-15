import sys
import os
from datetime import datetime
from typing import Optional

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.query_generator import QueryGeneratorService
from services.facebook_search import FacebookSearchService
from services.facebook_scraper import FacebookScraperService
from services.gemini_service import GeminiService
from services.logger import LoggerService
from models.scraping_result import ScrapingResult

class ScrapingOrchestrator:
    """Orchestrator scrapingu - koordynuje proces scrapingu Facebook"""
    
    def __init__(self):
        self.query_generator = QueryGeneratorService()
        self.facebook_search = FacebookSearchService()
        self.facebook_scraper = FacebookScraperService()
        self.gemini_service = GeminiService()
        self.logger = LoggerService()
        
        # Parametry dla iteracyjnego pobierania
        self.target_posts = 20  # Docelowa liczba postów
        self.initial_limit = 20  # Początkowy limit dla Apify
        self.max_limit = 100  # Maksymalny limit (zabezpieczenie)
        self.limit_multiplier = 2.0  # Mnożnik przy zwiększaniu limitu
        
        # Parametry weryfikacji Gemini
        self.enable_gemini_verification = True  # Włącz/wyłącz weryfikację
    
    def execute_scraping_job(
        self, 
        brand_name: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        progress_callback=None
    ) -> list[ScrapingResult]:
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
            
            # Krok 3: Scrapuj posty z filtrowaniem po dacie (priorytetyzacja)
            all_results = []
            
            # Parsuj daty jeśli podane
            start_dt = self._parse_date(start_date) if start_date else None
            end_dt = self._parse_date(end_date) if end_date else None
            
            # Najpierw wzmianki (najbardziej istotne)
            if urls_dict["mentions"] and len(all_results) < self.target_posts:
                if progress_callback:
                    progress_callback("Pobieranie postów ze wzmianek...", 0.3)
                results = self._scrape_with_date_filter(
                    urls_dict["mentions"][:10], 
                    "post", 
                    start_dt, 
                    end_dt,
                    target_count=self.target_posts,
                    current_count=len(all_results),
                    max_posts_per_url=1,
                    progress_callback=progress_callback,
                    brand_name=brand_name
                )
                all_results = self._merge_without_duplicates(all_results, results)
            
            # Grupy
            if urls_dict["groups"] and len(all_results) < self.target_posts:
                if progress_callback:
                    progress_callback("Pobieranie postów z grup...", 0.5)
                results = self._scrape_with_date_filter(
                    urls_dict["groups"][:5], 
                    "group", 
                    start_dt, 
                    end_dt,
                    target_count=self.target_posts,
                    current_count=len(all_results),
                    max_posts_per_url=15,
                    progress_callback=progress_callback,
                    brand_name=brand_name
                )
                all_results = self._merge_without_duplicates(all_results, results)
            
            # Wydarzenia
            if urls_dict["events"] and len(all_results) < self.target_posts:
                if progress_callback:
                    progress_callback("Pobieranie postów z wydarzeń...", 0.7)
                results = self._scrape_with_date_filter(
                    urls_dict["events"][:5], 
                    "event", 
                    start_dt, 
                    end_dt,
                    target_count=self.target_posts,
                    current_count=len(all_results),
                    max_posts_per_url=10,
                    progress_callback=progress_callback,
                    brand_name=brand_name
                )
                all_results = self._merge_without_duplicates(all_results, results)
            
            # Strony
            if urls_dict["pages"] and len(all_results) < self.target_posts:
                if progress_callback:
                    progress_callback("Pobieranie postów ze stron...", 0.8)
                results = self._scrape_with_date_filter(
                    urls_dict["pages"][:5], 
                    "page", 
                    start_dt, 
                    end_dt,
                    target_count=self.target_posts,
                    current_count=len(all_results),
                    max_posts_per_url=10,
                    progress_callback=progress_callback,
                    brand_name=brand_name
                )
                all_results = self._merge_without_duplicates(all_results, results)
            
            # Usuń duplikaty (ostateczne sprawdzenie)
            unique_results = self._remove_duplicates_by_url(all_results)
            
            # Ogranicz do docelowej liczby
            final_results = unique_results[:self.target_posts]
            
            self.logger.add_log(
                f"Zebrano {len(final_results)} unikalnych wyników "
                f"(cel: {self.target_posts}, po filtrowaniu daty: {start_date or 'brak'} - {end_date or 'brak'})"
            )
            
            if len(final_results) < self.target_posts:
                self.logger.add_log(
                    f"Uwaga: Zebrano tylko {len(final_results)} postów z {self.target_posts} docelowych. "
                    f"Możliwe przyczyny: brak postów w zakresie daty lub ograniczenia API.",
                    "WARNING"
                )
            
            return final_results
            
        except Exception as e:
            self.logger.add_log(f"Błąd scrapingu: {str(e)}", "ERROR")
            raise
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parsuje string daty (YYYY-MM-DD) do datetime"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            self.logger.add_log(f"Nieprawidłowy format daty: {date_str}", "WARNING")
            return None
    
    def _filter_by_date_range(
        self, 
        results: list[ScrapingResult], 
        start_date: Optional[datetime], 
        end_date: Optional[datetime]
    ) -> list[ScrapingResult]:
        """Filtruje wyniki po zakresie dat"""
        if not start_date and not end_date:
            return results  # Brak filtrowania jeśli nie podano dat
        
        filtered = []
        for result in results:
            # Jeśli post nie ma daty, zachowaj go (może być przydatny)
            if not result.date:
                filtered.append(result)
                continue
            
            # Sprawdź czy data jest w zakresie
            # Porównaj tylko daty (bez czasu) - posty z dnia start_date i end_date są OK
            result_date_only = result.date.date()
            
            if start_date:
                start_date_only = start_date.date()
                if result_date_only < start_date_only:
                    continue  # Za wcześnie
            
            if end_date:
                end_date_only = end_date.date()
                if result_date_only > end_date_only:
                    continue  # Za późno
            
            filtered.append(result)
        
        return filtered
    
    def _scrape_with_date_filter(
        self,
        urls: list[str],
        url_type: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        target_count: int,
        current_count: int,
        max_posts_per_url: int,
        progress_callback=None,
        brand_name: str = ""
    ) -> list[ScrapingResult]:
        """
        Pobiera posty z filtrowaniem po dacie, zwiększając limit jeśli potrzeba
        aby osiągnąć docelową liczbę postów
        """
        if not urls:
            return []
        
        limit = self.initial_limit
        all_filtered = []
        seen_urls = set()  # Do śledzenia duplikatów
        
        needed_count = target_count - current_count
        if needed_count <= 0:
            return []
        
        while len(all_filtered) < needed_count and limit <= self.max_limit:
            # Pobierz z Apify
            try:
                results = self.facebook_scraper.scrape_urls_parallel(
                    urls, url_type, max_posts_per_url=min(limit, max_posts_per_url)
                )
            except Exception as e:
                self.logger.add_log(f"Błąd podczas pobierania: {str(e)}", "WARNING")
                break
            
            if not results:
                # Brak wyników - prawdopodobnie nie ma więcej danych
                break
            
            # Konwertuj do ScrapingResult
            converted = self._convert_to_results(results)
            
            # Usuń duplikaty (po URL) - tylko nowe, których jeszcze nie widzieliśmy
            unique_converted = []
            for result in converted:
                if result.url and result.url not in seen_urls:
                    seen_urls.add(result.url)
                    unique_converted.append(result)
            
            # Filtruj po dacie
            filtered = self._filter_by_date_range(unique_converted, start_date, end_date)
            
            # Weryfikacja przez Gemini (jeśli włączona)
            if self.enable_gemini_verification and filtered and brand_name:
                verified = self._verify_posts_with_gemini(
                    filtered, 
                    brand_name, 
                    start_date.strftime("%Y-%m-%d") if start_date else None,
                    end_date.strftime("%Y-%m-%d") if end_date else None
                )
                filtered = verified
            
            # Dodaj do zbioru (już są bez duplikatów, bo seen_urls jest wspólne)
            all_filtered.extend(filtered)
            
            # Jeśli mamy wystarczająco, zwróć
            if len(all_filtered) >= needed_count:
                return all_filtered[:needed_count]
            
            # Jeśli wszystkie pobrane posty były poza zakresem daty
            if len(filtered) == 0 and len(unique_converted) > 0:
                # Wszystkie posty były poza zakresem - prawdopodobnie nie ma więcej w zakresie
                self.logger.add_log(
                    f"Wszystkie {len(unique_converted)} pobrane posty były poza zakresem daty. "
                    f"Przerywam pobieranie dla {url_type}.",
                    "INFO"
                )
                break
            
            # Jeśli pobraliśmy mniej niż limit, prawdopodobnie nie ma więcej danych
            if len(results) < limit:
                break
            
            # Zwiększ limit i spróbuj ponownie
            old_limit = limit
            limit = min(int(limit * self.limit_multiplier), self.max_limit)
            self.logger.add_log(
                f"Po filtrowaniu zostało {len(all_filtered)}/{needed_count} postów. "
                f"Zwiększam limit z {old_limit} do {limit}.",
                "INFO"
            )
        
        return all_filtered
    
    def _merge_without_duplicates(
        self, 
        existing: list[ScrapingResult], 
        new: list[ScrapingResult]
    ) -> list[ScrapingResult]:
        """Łączy dwie listy wyników usuwając duplikaty po URL"""
        seen_urls = {r.url for r in existing if r.url}
        merged = list(existing)
        
        for result in new:
            if result.url and result.url not in seen_urls:
                seen_urls.add(result.url)
                merged.append(result)
        
        return merged
    
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
    
    def _verify_posts_with_gemini(
        self,
        results: list[ScrapingResult],
        brand_name: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> list[ScrapingResult]:
        """
        Weryfikuje posty przez Gemini Flash Lite:
        - Sprawdza czy data jest w zakresie (na podstawie treści)
        - Sprawdza czy post jest na temat marki
        """
        if not results:
            return []
        
        verified_results = []
        rejected_count = 0
        
        self.logger.add_log(f"Weryfikacja {len(results)} postów przez Gemini...")
        
        for result in results:
            try:
                # Przygotuj datę do weryfikacji
                post_date_str = result.date.strftime("%Y-%m-%d") if result.date else "nieznana"
                
                # Wywołaj Gemini
                verification = self.gemini_service.verify_post(
                    post_text=result.text,
                    post_date=post_date_str,
                    brand_name=brand_name,
                    start_date=start_date or "brak",
                    end_date=end_date or "brak"
                )
                
                if verification.get("valid", False):
                    verified_results.append(result)
                else:
                    rejected_count += 1
                    self.logger.add_log(
                        f"Odrzucono post (Gemini): {verification.get('reason', 'Brak powodu')}",
                        "INFO"
                    )
                    
            except Exception as e:
                # W przypadku błędu, zaakceptuj post (fail-safe)
                self.logger.add_log(
                    f"Błąd weryfikacji posta (zaakceptowano): {str(e)}",
                    "WARNING"
                )
                verified_results.append(result)
        
        self.logger.add_log(
            f"Weryfikacja zakończona: {len(verified_results)}/{len(results)} postów zaakceptowanych, "
            f"{rejected_count} odrzuconych"
        )
        
        return verified_results
