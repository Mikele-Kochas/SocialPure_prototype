from datetime import datetime

def validate_scraping_request(data: dict) -> tuple[bool, str]:
    """Waliduje dane requestu scrapingu"""
    brand_name = data.get('brand_name', '').strip()
    start_date = data.get('start_date', '')
    end_date = data.get('end_date', '')
    
    # Walidacja brand_name
    if not brand_name:
        return False, "Nazwa marki jest wymagana"
    
    if len(brand_name) > 200:
        return False, "Nazwa marki jest zbyt długa (max 200 znaków)"
    
    # Walidacja dat
    if not start_date or not end_date:
        return False, "Obie daty są wymagane"
    
    if not validate_date(start_date):
        return False, "Nieprawidłowy format daty początkowej (wymagany: YYYY-MM-DD)"
    
    if not validate_date(end_date):
        return False, "Nieprawidłowy format daty końcowej (wymagany: YYYY-MM-DD)"
    
    # Sprawdź czy start < end
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start >= end:
            return False, "Data początkowa musi być wcześniejsza niż data końcowa"
    except ValueError:
        return False, "Nieprawidłowy format dat"
    
    return True, ""

def validate_date(date_str: str) -> bool:
    """Sprawdza format daty YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_brand_name(brand_name: str) -> tuple[bool, str]:
    """Waliduje nazwę marki"""
    if not brand_name or not brand_name.strip():
        return False, "Nazwa marki nie może być pusta"
    
    if len(brand_name) > 200:
        return False, "Nazwa marki jest zbyt długa (max 200 znaków)"
    
    return True, ""
