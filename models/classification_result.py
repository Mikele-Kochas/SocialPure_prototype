from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ClassificationResult:
    """Model danych: wynik klasyfikacji komentarza"""
    comment_text: str
    category: str
    sentiment: str  # "pozytywny"/"negatywny"/"neutralny"
    comment_index: int = 0
    classified_at: datetime = None
    
    def __post_init__(self):
        if self.classified_at is None:
            self.classified_at = datetime.now()
        
        # Walidacja sentimentu
        if self.sentiment not in ['pozytywny', 'negatywny', 'neutralny']:
            self.sentiment = 'neutralny'
    
    def to_dict(self):
        """Konwersja do słownika"""
        return {
            "comment_text": self.comment_text,
            "category": self.category,
            "sentiment": self.sentiment,
            "comment_index": self.comment_index,
            "classified_at": self.classified_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Tworzenie z słownika"""
        result = cls(
            comment_text=data.get("comment_text", ""),
            category=data.get("category", ""),
            sentiment=data.get("sentiment", "neutralny"),
            comment_index=data.get("comment_index", 0)
        )
        if data.get("classified_at"):
            try:
                result.classified_at = datetime.fromisoformat(data["classified_at"])
            except:
                pass
        return result
    
    def get_sentiment_emoji(self) -> str:
        """Zwraca emoji dla sentimentu"""
        emoji_map = {
            'pozytywny': '😊',
            'negatywny': '😞',
            'neutralny': '😐'
        }
        return emoji_map.get(self.sentiment, '❓')
