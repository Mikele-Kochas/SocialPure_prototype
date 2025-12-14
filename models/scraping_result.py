from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ScrapingResult:
    """Model danych: wynik scrapingu z Facebook"""
    text: str
    url: str
    author: str = ""
    date: Optional[datetime] = None
    source_type: str = "post"  # "post"/"comment"/"group"/"event"
    platform: str = "facebook"
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self):
        """Konwersja do słownika"""
        return {
            "text": self.text,
            "url": self.url,
            "author": self.author,
            "date": self.date.isoformat() if self.date else None,
            "source_type": self.source_type,
            "platform": self.platform,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_apify_item(cls, item: dict):
        """Tworzenie z danych Apify"""
        # Wyciągnij tekst z różnych pól
        text = item.get("text") or item.get("postText") or item.get("message") or ""
        
        # Wyciągnij URL
        url = item.get("url") or item.get("postUrl") or ""
        
        # Wyciągnij autora
        author = item.get("author") or item.get("authorName") or ""
        
        # Wyciągnij datę - Apify zwraca "time" lub "createdAt"
        date = None
        date_str = item.get("time") or item.get("createdAt") or item.get("timestamp")
        
        if date_str:
            try:
                from dateutil import parser as date_parser
                # Jeśli to timestamp (liczba), konwertuj
                if isinstance(date_str, (int, float)):
                    date = datetime.fromtimestamp(date_str)
                else:
                    # Jeśli to string, parsuj
                    date = date_parser.parse(str(date_str))
            except Exception as e:
                # Fallback: spróbuj z timestamp jeśli jest dostępny
                if item.get("timestamp"):
                    try:
                        date = datetime.fromtimestamp(item.get("timestamp"))
                    except:
                        pass
        
        # Określ typ źródła
        source_type = "post"
        if "/groups/" in url.lower():
            source_type = "group"
        elif "/events/" in url.lower():
            source_type = "event"
        
        return cls(
            text=text.strip(),
            url=url,
            author=author,
            date=date,
            source_type=source_type,
            metadata=item
        )
