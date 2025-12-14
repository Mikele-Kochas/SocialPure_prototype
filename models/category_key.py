from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict

@dataclass
class CategoryKey:
    """Model danych: klucz kategorii wygenerowany przez Agent 2 (ABSA)"""
    job_id: str
    categories: List[Dict[str, str]] = field(default_factory=list)
    prompt_type: str = "ABSA"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        """Konwersja do słownika"""
        return {
            "job_id": self.job_id,
            "categories": self.categories,
            "prompt_type": self.prompt_type,
            "created_at": self.created_at.isoformat()
        }
    
    def get_category_names(self):
        """Zwraca listę nazw kategorii"""
        return [cat.get("aspekt", "") for cat in self.categories]
    
    def find_category_definition(self, category_name: str) -> str:
        """Znajdź definicję kategorii"""
        for cat in self.categories:
            if cat.get("aspekt", "").strip().lower() == category_name.lower():
                return cat.get("definicja", "")
        return ""
    
    def format_for_display(self) -> str:
        """Formatowanie do wyświetlenia (Markdown)"""
        output = "### 📋 Wygenerowane Aspekty (ABSA)\n\n"
        for i, item in enumerate(self.categories, 1):
            nazwa = item.get('aspekt', 'Brak nazwy')
            definicja = item.get('definicja', 'Brak definicji')
            output += f"**{i}. {nazwa}**\n"
            output += f"   _{definicja}_\n\n"
        return output
