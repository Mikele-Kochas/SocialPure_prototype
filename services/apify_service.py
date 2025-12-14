import time
import sys
import os
from apify_client import ApifyClient

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import APIFY_API_TOKEN, SCRAPING_TIMEOUT
from services.logger import LoggerService

class ApifyService:
    """Serwis Apify - integracja z Apify Client"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.client = ApifyClient(APIFY_API_TOKEN)
        self.logger = LoggerService()
        
        # Actor IDs
        self.FACEBOOK_POSTS_ACTOR = "apify/facebook-posts-scraper"
        self.GOOGLE_SEARCH_ACTOR = "apify/google-search-scraper"
        
        self._initialized = True
    
    def run_actor(self, actor_id: str, run_input: dict, timeout: int = None) -> dict:
        """Uruchamia actora Apify"""
        timeout = timeout or SCRAPING_TIMEOUT
        self.logger.add_log(f"Uruchamiam Actor: {actor_id}")
        
        run = self.client.actor(actor_id).call(run_input=run_input, timeout_secs=timeout)
        return {
            "run_id": run.get("id"),
            "defaultDatasetId": run.get("defaultDatasetId")
        }
    
    def wait_for_completion(self, run_id: str, max_wait: int = None) -> str:
        """Czeka na zakończenie run'a"""
        max_wait = max_wait or SCRAPING_TIMEOUT
        waited = 0
        
        while waited < max_wait:
            run_info = self.client.run(run_id).get()
            status = run_info.get("status")
            
            if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
                self.logger.add_log(f"Run {run_id} zakończony ze statusem: {status}")
                return status
            
            time.sleep(5)
            waited += 5
        
        return "TIMED-OUT"
    
    def get_dataset_items(self, dataset_id: str) -> list:
        """Pobiera wszystkie itemy z dataset"""
        if not dataset_id:
            return []
        
        items = []
        try:
            for item in self.client.dataset(dataset_id).iterate_items():
                items.append(item)
        except Exception as e:
            self.logger.add_log(f"Błąd pobierania dataset {dataset_id}: {str(e)}", "ERROR")
        
        return items
    
    def run_google_search(self, query: str, max_results: int = 20) -> list:
        """Wrapper dla Google Search Actor"""
        run_input = {
            "queries": query,
            "maxResults": max_results,
        }
        
        run_data = self.run_actor(self.GOOGLE_SEARCH_ACTOR, run_input)
        run_id = run_data["run_id"]
        
        status = self.wait_for_completion(run_id)
        if status != "SUCCEEDED":
            return []
        
        dataset_id = run_data.get("defaultDatasetId")
        return self.get_dataset_items(dataset_id)
    
    def run_facebook_scraper(self, urls: list[str], max_posts: int = 20) -> list:
        """Wrapper dla Facebook Posts Scraper"""
        run_input = {
            "startUrls": [{"url": url} for url in urls],
            "maxPosts": max_posts,
        }
        
        run_data = self.run_actor(self.FACEBOOK_POSTS_ACTOR, run_input)
        run_id = run_data["run_id"]
        
        status = self.wait_for_completion(run_id)
        if status != "SUCCEEDED":
            return []
        
        dataset_id = run_data.get("defaultDatasetId")
        return self.get_dataset_items(dataset_id)
