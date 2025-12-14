import json
import sys
import os
import google.generativeai as genai

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY
from services.logger import LoggerService

class QueryGeneratorService:
    """Serwis generowania zapytań wyszukiwania"""
    
    def __init__(self):
        self.logger = LoggerService()
        genai.configure(api_key=GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    
    def generate_advanced_search_queries(self, brand_name: str) -> list[str]:
        """Generuje zaawansowane zapytania wyszukiwania używając Gemini"""
        try:
            self.logger.add_log(f"Generuję zapytania wyszukiwania dla: {brand_name}")
            
            prompt = f"""
Jesteś ekspertem od monitoringu wizerunku marki w mediach społecznościowych. Dla marki/organizacji "{brand_name}" wygeneruj różnorodne zapytania wyszukiwania, które pomogą znaleźć WSZYSTKIE wzmianki o tej marce na Facebooku.

WAŻNE: Szukamy wzmianek od użytkowników, w grupach, wydarzeniach, komentarzach - NIE TYLKO oficjalnych stron.

Wygeneruj zapytania które znajdą:
1. Posty użytkowników wspominające markę
2. Wzmianki w grupach tematycznych
3. Wzmianki w wydarzeniach
4. Komentarze pod postami
5. Hashtagi związane z marką
6. Wzmianki w różnych językach/wariantach nazwy

Uwzględnij:
- Pełną nazwę: "{brand_name}"
- Popularne skróty i warianty
- Warianty bez polskich znaków
- Synonimy i alternatywne nazwy
- Kontekstowe frazy (np. "studia na", "uczę się w", "pracuję w")

Zwróć JSON z listą maksymalnie 20 różnych zapytań wyszukiwania:
{{
  "queries": [
    "zapytanie 1",
    "zapytanie 2",
    ...
  ]
}}

Każde zapytanie powinno być gotowe do użycia w wyszukiwaniu Facebook.
"""
            
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parsuj JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                response_text = response_text[json_start:json_end].strip()
            
            try:
                data = json.loads(response_text)
                queries = data.get("queries", [])
                
                # Dodaj podstawowe zapytania jako fallback
                base_queries = [
                    f"{brand_name} Facebook",
                    f"{brand_name} posty",
                    f"{brand_name} wzmianki"
                ]
                
                all_queries = base_queries + queries[:17]  # Max 20 łącznie
                self.logger.add_log(f"Wygenerowano {len(all_queries)} zapytań wyszukiwania")
                
                return all_queries
                
            except json.JSONDecodeError:
                self.logger.add_log("Błąd parsowania JSON, używam podstawowych zapytań", "WARNING")
                return self.generate_fallback_queries(brand_name)
                
        except Exception as e:
            self.logger.add_log(f"Błąd generowania zapytań: {str(e)}", "ERROR")
            return self.generate_fallback_queries(brand_name)
    
    def generate_fallback_queries(self, brand_name: str) -> list[str]:
        """Podstawowe zapytania bez Gemini"""
        return [
            f"{brand_name} Facebook",
            f"{brand_name} posty",
            f"{brand_name} wzmianki",
            f"{brand_name} grupy",
            f"{brand_name} wydarzenia"
        ]
