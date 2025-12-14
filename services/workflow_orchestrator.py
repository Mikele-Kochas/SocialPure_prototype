"""
Główny orchestrator workflow - koordynuje cały proces: Scraping → Klasyfikacja → Raport

TODO:
- [ ] Utwórz klasę WorkflowOrchestrator
- [ ] W __init__:
    - ScrapingOrchestrator
    - ClassificationOrchestrator
    - VisualizationService
    - ReportService
    - JobStorageService
    - LoggerService
- [ ] Metoda execute_full_pipeline(job: ScrapingJob) -> ScrapingJob:
    - Główna funkcja całego workflow
    - Krok 1: Scraping (Agent 1)
        - job.status = "scraping"
        - job.progress = 0.1
        - Wywołaj ScrapingOrchestrator.execute_scraping_job()
        - Zapisz wyniki do job.scraping_results
        - job.progress = 0.3
    - Krok 2-4: Klasyfikacja
        - job.status = "classifying"
        - job.current_step = "generating_key"
        - job.progress = 0.4
        - Wywołaj ClassificationOrchestrator.execute_classification_pipeline()
        - Zapisz wyniki do job (category_key, classification_results, report)
        - job.progress = 0.8
    - Krok 5: Wizualizacje
        - job.current_step = "generating_visualizations"
        - Wywołaj VisualizationService.generate_all_charts()
        - Zapisz ścieżki do wykresów w job
        - job.progress = 0.9
    - Krok 6: Finalizacja raportu
        - job.current_step = "finalizing_report"
        - Wywołaj ReportService.finalize_report()
        - Wstaw wykresy do raportu
        - Zapisz finalny raport do job.report
    - Finalizacja:
        - job.status = "completed"
        - job.progress = 1.0
        - Zapisz job przez JobStorageService
    - Obsłuż błędy:
        - job.status = "failed"
        - job.error_message = str(e)
        - Zapisz job
    - Zwraca zaktualizowany job
- [ ] Metoda _update_job_progress(job: ScrapingJob, step: str, progress: float):
    - Aktualizuje job.progress i job.current_step
    - Zapisuje job przez JobStorageService
- [ ] Dodaj logowanie przez LoggerService
"""

