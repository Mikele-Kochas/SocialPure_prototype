import json
import sys
import os
import google.generativeai as genai

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY

# Prompt dla ABSA (analityk marketingowy)
PROMPT_ABSA = """Jesteś analitykiem marketingowym (Customer Experience analyst) badającym opinie klientów na temat "{brand_name}".

Twoim zadaniem jest stworzenie klucza do **Analizy Aspektowej Sentymentu (ABSA)** na podstawie poniższych opinii.

<dane_tekstowe>
{data}
</dane_tekstowe>

Nie twórz kategorii ogólnych (np. "pozytywne opinie") ani tematów.
Skup się wyłącznie na identyfikacji **konkretnych ASPEKTÓW** (cech, atrybutów) usługi/produktu/organizacji, o których piszą użytkownicy.

Zwróć wynik wyłącznie jako listę JSON, według schematu:
[
  {{
    "aspekt": "Nazwa pierwszego aspektu (np. 'Cena', 'Obsługa klienta', 'Aplikacja mobilna', 'Jakość nauczania', 'Infrastruktura')",
    "definicja": "Opis, czego dotyczy ten aspekt."
  }},
  {{
    "aspekt": "Nazwa drugiego aspektu",
    "definicja": "..."
  }}
]

Wygeneruj 5-7 aspektów na podstawie analizy wszystkich opinii."""

class GeminiService:
    """Serwis Gemini - integracja z Google Gemini API"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.flash_model = genai.GenerativeModel('gemini-2.5-flash')
        self.flash_lite_model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self._initialized = True
    
    def generate_category_key(self, comments: list[str], brand_name: str) -> dict:
        """
        Agent 2: Generuje klucz kategorii (ABSA)
        Używa: gemini-2.5-flash
        """
        if not comments:
            raise ValueError("Brak komentarzy do analizy")
        
        # Przygotuj prompt
        comments_text = "\n".join([f"- {c}" for c in comments])
        prompt = PROMPT_ABSA.format(brand_name=brand_name, data=comments_text)
        
        # Wywołaj API
        response = self.flash_model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parsuj JSON
        return self.parse_json_response(response_text)
    
    def parse_json_response(self, response_text: str):
        """Parsuje JSON z odpowiedzi Gemini - ulepszona wersja (może zwrócić list lub dict)"""
        original_text = response_text
        
        # Krok 1: Usuń markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        
        # Krok 2: Znajdź JSON array lub object
        # Szukaj pierwszego [
        if "[" in response_text:
            json_start = response_text.find("[")
            # Znajdź odpowiadający ]
            bracket_count = 0
            json_end = json_start
            for i in range(json_start, len(response_text)):
                if response_text[i] == "[":
                    bracket_count += 1
                elif response_text[i] == "]":
                    bracket_count -= 1
                    if bracket_count == 0:
                        json_end = i + 1
                        break
            response_text = response_text[json_start:json_end].strip()
        
        # Krok 3: Usuń ewentualne komentarze markdown przed/po
        lines = response_text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Pomiń linie które wyglądają jak markdown formatting
            if line.strip().startswith('**') or line.strip().startswith('*') and not line.strip().startswith('"'):
                continue
            cleaned_lines.append(line)
        response_text = '\n'.join(cleaned_lines)
        
        # Krok 4: Spróbuj sparsować
        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                # Jeśli to dict, sprawdź czy ma klucz z listą
                for key in ['categories', 'aspekty', 'items', 'results']:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                # Jeśli nie, zwróć dict (może być pojedynczy wynik klasyfikacji)
                return parsed
            else:
                return []
        except json.JSONDecodeError:
            # Krok 5: Fallback - spróbuj znaleźć JSON ręcznie używając regex
            import re
            # Szukaj wzorca [{...}]
            json_pattern = r'\[\s*\{[^}]+\}(?:\s*,\s*\{[^}]+\})*\s*\]'
            matches = re.findall(json_pattern, original_text, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches[0])
                except:
                    pass
            
            # Ostatnia próba - wyciągnij tylko obiekty z "aspekt" i "definicja"
            items = []
            aspekt_pattern = r'"aspekt"\s*:\s*"([^"]+)"'
            definicja_pattern = r'"definicja"\s*:\s*"([^"]+)"'
            
            aspekty = re.findall(aspekt_pattern, original_text)
            definicje = re.findall(definicja_pattern, original_text)
            
            if aspekty and definicje and len(aspekty) == len(definicje):
                for a, d in zip(aspekty, definicje):
                    items.append({"aspekt": a, "definicja": d})
                if items:
                    return items
            
            raise ValueError(f"Błąd parsowania JSON. Odpowiedź: {original_text[:500]}")
    
    def verify_post(
        self, 
        post_text: str, 
        post_date: str, 
        brand_name: str, 
        start_date: str, 
        end_date: str
    ) -> dict:
        """
        Weryfikuje post przez Gemini Flash Lite:
        - Sprawdza czy post jest na temat marki
        
        Zwraca: {"valid": bool, "reason": str}
        """
        prompt = f"""Jesteś ekspertem weryfikującym posty z mediów społecznych.

<post>
{post_text}
</post>

<marka>
{brand_name}
</marka>

Wykonaj JEDNO sprawdzenie:

**Weryfikacja relevancy:**
- Czy post dotyczy marki/organizacji "{brand_name}"?
- Czy jest to opinia, komentarz lub wzmianka o tej marce?
- Czy post jest na temat (nie spam, nie reklama innej marki)?

Zwróć wynik w formacie JSON:
{{
  "valid": true/false,
  "relevant_to_brand": true/false,
  "reason": "Krótkie wyjaśnienie decyzji"
}}

Post jest WAŻNY jeśli:
- Post dotyczy marki "{brand_name}"

Jeśli warunek nie jest spełniony, ustaw "valid": false."""

        try:
            response = self.flash_lite_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parsuj JSON
            result = self.parse_json_response(response_text)
            
            # Normalizuj wynik
            if isinstance(result, dict):
                return {
                    "valid": result.get("valid", False),
                    "relevant_to_brand": result.get("relevant_to_brand", False),
                    "reason": result.get("reason", "Brak wyjaśnienia")
                }
            else:
                # Jeśli nie dict, załóż że nieprawidłowy
                return {
                    "valid": False,
                    "relevant_to_brand": False,
                    "reason": "Błąd parsowania odpowiedzi Gemini"
                }
        except Exception as e:
            # W przypadku błędu, zaakceptuj post (fail-safe)
            return {
                "valid": True,
                "relevant_to_brand": True,
                "reason": f"Błąd weryfikacji (zaakceptowano): {str(e)}"
            }