import uuid
from datetime import datetime

def generate_job_id() -> str:
    """Generuje UUID dla zadania"""
    return str(uuid.uuid4())

def format_datetime(dt: datetime) -> str:
    """Formatuje datetime do czytelnego stringa"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_date(date_str: str) -> datetime:
    """Parsuje string daty (YYYY-MM-DD) do datetime"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Nieprawidłowy format daty: {date_str}")

def calculate_progress(current: int, total: int) -> float:
    """Oblicza progress (0.0 - 1.0)"""
    if total == 0:
        return 0.0
    return min(1.0, max(0.0, current / total))
