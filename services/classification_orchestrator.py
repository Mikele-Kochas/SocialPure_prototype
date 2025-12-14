"""
Orchestrator klasyfikacji - koordynuje proces klasyfikacji komentarzy

TODO:
- [ ] Utwórz klasę ClassificationOrchestrator
- [ ] W __init__:
    - GeminiService
    - LoggerService
- [ ] Metoda execute_classification_pipeline(
        job: ScrapingJob,
        scraping_results: list[ScrapingResult]
    ) -> tuple[CategoryKey, list[ClassificationResult], str]:
    - Pełny pipeline klasyfikacji
    - Krok 1: Wyciągnij teksty z ScrapingResult
    - Krok 2: Generuj klucz kategorii (Agent 2 - Gemini Flash)
        - Użyj GeminiService.generate_category_key()
        - Utwórz CategoryKey object
    - Krok 3: Klasyfikuj komentarze (Agent 3 - Gemini Flash Lite)
        - Dla każdego ScrapingResult:
            - Wywołaj GeminiService.classify_comment()
            - Utwórz ClassificationResult
        - Optymalizacja: użyj classify_batch() jeśli możliwe
    - Krok 4: Generuj raport (Agent 4 - Gemini Flash)
        - Użyj GeminiService.generate_report()
        - Zwróć Markdown raportu
    - Zwraca: (CategoryKey, list[ClassificationResult], str report)
    - Aktualizuj job.progress na każdym kroku
- [ ] Metoda _extract_comments(scraping_results: list[ScrapingResult]) -> list[str]:
    - Wyciąga teksty komentarzy z ScrapingResult
    - Filtruje puste teksty
    - Zwraca listę stringów
- [ ] Metoda _classify_all_comments(
        comments: list[str],
        category_key: CategoryKey
    ) -> list[ClassificationResult]:
    - Klasyfikuje wszystkie komentarze
    - Używa GeminiService.classify_batch() lub pętli classify_comment()
    - Zwraca listę ClassificationResult
- [ ] Dodaj logowanie przez LoggerService
"""

