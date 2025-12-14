"""
Blueprint API - REST API endpoints (JSON)

TODO:
- [ ] Utwórz blueprint: api_bp = Blueprint('api', __name__, url_prefix='/api')
- [ ] Zaimportuj potrzebne serwisy i modele
- [ ] Route POST /api/scrape:
    - Odbiera JSON: {"brand_name": str, "start_date": str, "end_date": str}
    - Waliduje dane
    - Tworzy ScrapingJob
    - Uruchamia workflow w tle
    - Zwraca JSON: {"job_id": str, "status": "pending"}
- [ ] Route GET /api/job/<job_id>:
    - Zwraca pełne dane zadania jako JSON
    - Status 404 jeśli nie istnieje
- [ ] Route GET /api/job/<job_id>/status:
    - Zwraca tylko status i progress jako JSON
- [ ] Route GET /api/job/<job_id>/results:
    - Zwraca wyniki scrapingu jako JSON
- [ ] Route GET /api/job/<job_id>/classification:
    - Zwraca wyniki klasyfikacji jako JSON
- [ ] Route GET /api/job/<job_id>/report:
    - Zwraca raport jako JSON (markdown string)
- [ ] Route GET /api/jobs:
    - Zwraca listę wszystkich zadań (podsumowanie)
- [ ] Route DELETE /api/job/<job_id>:
    - Usuwa zadanie
    - Zwraca {"success": bool}
- [ ] Dodaj CORS headers jeśli potrzebne
- [ ] Dodaj error handling z odpowiednimi kodami HTTP
- [ ] Dodaj walidację JSON requestów
"""

