from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from concurrent.futures import ThreadPoolExecutor
import sys
import os
import json

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.scraping_job import ScrapingJob
from models.category_key import CategoryKey
from models.classification_result import ClassificationResult
from services.job_storage import JobStorageService
from services.storage_service import StorageService
from services.scraping_orchestrator import ScrapingOrchestrator
from services.gemini_service import GeminiService
from services.report_service import ReportService
from services.logger import LoggerService
from utils.helpers import generate_job_id
from utils.validators import validate_scraping_request

scraping_bp = Blueprint('scraping', __name__)
job_storage = JobStorageService()
storage_service = StorageService()
scraping_orchestrator = ScrapingOrchestrator()
gemini_service = GeminiService()
report_service = ReportService()
logger = LoggerService()

# Thread pool dla długotrwałych zadań
executor = ThreadPoolExecutor(max_workers=2)

def run_classification_all(job_id: str):
    """Funkcja uruchamiana w tle: klasyfikuje wszystkie komentarze"""
    job = job_storage.get(job_id)
    if not job or not job.scraping_results or not job.category_key:
        return
    
    try:
        job.status = "classifying"
        job.update_progress("Klasyfikowanie komentarzy...", 0.5)
        job_storage.update(job)
        
        categories = job.category_key.categories
        category_key_text = json.dumps(categories, ensure_ascii=False, indent=2)
        
        total = len(job.scraping_results)
        classification_results = {}
        
        for idx, result in enumerate(job.scraping_results):
            try:
                comment_text = result.text
                if not comment_text or len(comment_text.strip()) < 5:
                    continue
                
                # Prompt dla klasyfikacji
                prompt = f"""Jesteś ekspertem w klasyfikacji tekstu i analizie sentymentu. Otrzymujesz klucz kategoryzacyjny oraz jeden komentarz do oceny.

<klucz_kategorii>
{category_key_text}
</klucz_kategorii>

<komentarz_do_oceny>
{comment_text}
</komentarz_do_oceny>

Wykonaj DWA zadania:
1. Przypisz komentarz do DOKŁADNIE JEDNEJ kategorii z klucza (użyj pola "aspekt").
2. Oceń sentiment (tonację emocjonalną) komentarza jako: "pozytywny", "negatywny" lub "neutralny".

Zwróć wynik w formacie JSON:
{{
  "kategoria": "nazwa_aspektu",
  "sentiment": "pozytywny/negatywny/neutralny"
}}

Nie dodawaj żadnych innych wyjaśnień, tylko czysty JSON."""
                
                # Wywołaj Gemini Flash Lite
                response = gemini_service.flash_lite_model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Parsuj odpowiedź
                parsed = gemini_service.parse_json_response(response_text)
                
                if isinstance(parsed, list):
                    result_data = parsed[0] if len(parsed) > 0 else {}
                else:
                    result_data = parsed if isinstance(parsed, dict) else {}
                
                category = result_data.get('kategoria', result_data.get('aspekt', 'Nieznana'))
                sentiment = result_data.get('sentiment', 'neutralny').lower()
                
                if sentiment not in ['pozytywny', 'negatywny', 'neutralny']:
                    sentiment = 'neutralny'
                
                classification_results[idx] = {
                    'category': category,
                    'sentiment': sentiment
                }
                
                # Aktualizuj progress
                progress = 0.5 + (idx + 1) / total * 0.4
                job.update_progress(f"Klasyfikowanie {idx+1}/{total}...", progress)
                job.classification_results = classification_results
                job_storage.update(job)
                
                # Zapisz do JSON co 5 komentarzy
                if (idx + 1) % 5 == 0:
                    try:
                        storage_service.save_job_to_json(job)
                    except:
                        pass
                
            except Exception as e:
                logger.add_log(f"Błąd klasyfikacji komentarza {idx}: {str(e)}", "WARNING")
                continue
        
        # Finalizacja
        job.status = "completed"
        job.update_progress("Klasyfikacja zakończona", 1.0)
        job.classification_results = classification_results
        job_storage.update(job)
        
        # Zapisz do JSON
        try:
            storage_service.save_job_to_json(job)
            logger.add_log(f"Zapisano klasyfikację zadania {job_id} do JSON")
        except Exception as e:
            logger.add_log(f"Błąd zapisywania klasyfikacji: {str(e)}", "WARNING")
        
    except Exception as e:
        job.status = "failed"
        job.error_message = f"Błąd klasyfikacji: {str(e)}"
        job_storage.update(job)
        logger.add_log(f"Błąd klasyfikacji zadania {job_id}: {str(e)}", "ERROR")

def run_scraping_and_generate_key(job_id: str, brand_name: str):
    """Funkcja uruchamiana w tle: scraping + generowanie klucza"""
    job = job_storage.get(job_id)
    if not job:
        return
    
    try:
        # Krok 1: Scraping
        job.status = "scraping"
        job.update_progress("Scraping Facebook...", 0.1)
        job_storage.update(job)
        
        def progress_callback(step: str, progress: float):
            job.update_progress(step, progress)
            job_storage.update(job)
        
        scraping_results = scraping_orchestrator.execute_scraping_job(brand_name, progress_callback)
        job.scraping_results = scraping_results
        job.update_progress("Scraping zakończony", 0.3)
        job_storage.update(job)
        
        if not scraping_results:
            job.status = "failed"
            job.error_message = "Nie znaleziono żadnych wyników"
            job_storage.update(job)
            return
        
        # Krok 2: Generowanie klucza kategorii
        job.status = "classifying"
        job.update_progress("Generowanie klucza kategorii...", 0.5)
        job_storage.update(job)
        
        comments = [r.text for r in scraping_results if r.text.strip()]
        if not comments:
            job.status = "failed"
            job.error_message = "Brak komentarzy do analizy"
            job_storage.update(job)
            return
        
        category_data = gemini_service.generate_category_key(comments, brand_name)
        category_key = CategoryKey(
            job_id=job_id,
            categories=category_data if isinstance(category_data, list) else [],
            prompt_type="ABSA"
        )
        job.category_key = category_key
        job.update_progress("Klucz kategorii wygenerowany", 0.8)
        job_storage.update(job)
        
        # Zakończenie
        job.status = "completed"
        job.update_progress("Zakończono", 1.0)
        job_storage.update(job)
        
        # Automatyczne zapisanie do JSON
        try:
            storage_service.save_job_to_json(job)
            logger.add_log(f"Zapisano zadanie {job_id} do JSON")
        except Exception as e:
            logger.add_log(f"Błąd zapisywania do JSON: {str(e)}", "WARNING")
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job_storage.update(job)
        logger.add_log(f"Błąd w zadaniu {job_id}: {str(e)}", "ERROR")

@scraping_bp.route('/')
def index():
    """Strona główna - formularz scrapingu"""
    # Pobierz listę zapisanych zadań
    saved_jobs = storage_service.list_saved_jobs()
    return render_template('scraping/index.html', saved_jobs=saved_jobs)

@scraping_bp.route('/scrape', methods=['POST'])
def start_scraping():
    """Uruchamia zadanie scrapingu + generowania klucza"""
    brand_name = request.form.get('brand_name', '').strip()
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    
    # Walidacja
    is_valid, error_msg = validate_scraping_request({
        'brand_name': brand_name,
        'start_date': start_date,
        'end_date': end_date
    })
    
    if not is_valid:
        return render_template('scraping/index.html', error=error_msg), 400
    
    # Utwórz zadanie
    job_id = generate_job_id()
    job = ScrapingJob(
        job_id=job_id,
        brand_name=brand_name,
        start_date=start_date,
        end_date=end_date,
        status="pending"
    )
    
    job_storage.save(job)
    
    # Uruchom w tle
    executor.submit(run_scraping_and_generate_key, job_id, brand_name)
    
    return redirect(url_for('scraping.view_results', job_id=job_id))

@scraping_bp.route('/results/<job_id>')
def view_results(job_id: str):
    """Wyświetla wyniki zadania"""
    job = job_storage.get(job_id)
    
    # Jeśli nie ma w pamięci, spróbuj wczytać z JSON
    if not job:
        try:
            filepath = os.path.join(storage_service.data_dir, f"job_{job_id}.json")
            if os.path.exists(filepath):
                job = storage_service.load_job_from_json(filepath)
                # Załaduj do pamięci
                job_storage.save(job)
        except:
            pass
    
    if not job:
        return render_template('scraping/error.html', message="Zadanie nie znalezione"), 404
    
    return render_template('scraping/results.html', job=job)

@scraping_bp.route('/classification')
def classification():
    """Strona klasyfikacji - wybór zadania"""
    # Pobierz zadania z pamięci
    jobs = job_storage.get_all()
    completed_jobs = [j for j in jobs if j.status == "completed" and j.scraping_results]
    
    # Pobierz również zapisane zadania z JSON
    saved_jobs_data = storage_service.list_saved_jobs()
    saved_jobs = []
    for job_data in saved_jobs_data:
        if job_data.get("results_count", 0) > 0:
            try:
                job = storage_service.load_job_from_json(job_data["filepath"])
                # Sprawdź czy nie ma już w pamięci
                if not any(j.job_id == job.job_id for j in completed_jobs):
                    completed_jobs.append(job)
            except:
                continue
    
    return render_template('scraping/classification.html', jobs=completed_jobs)

@scraping_bp.route('/classification/<job_id>')
def classification_results(job_id: str):
    """Wyświetla klasyfikację dla wybranego zadania"""
    job = job_storage.get(job_id)
    
    # Jeśli nie ma w pamięci, spróbuj wczytać z JSON
    if not job:
        try:
            filepath = os.path.join(storage_service.data_dir, f"job_{job_id}.json")
            if os.path.exists(filepath):
                job = storage_service.load_job_from_json(filepath)
                # Załaduj do pamięci
                job_storage.save(job)
        except:
            pass
    
    if not job:
        return render_template('scraping/error.html', message="Zadanie nie znalezione"), 404
    
    if job.status != "completed" or not job.scraping_results:
        return render_template('scraping/error.html', message="Zadanie nie zostało jeszcze zakończone"), 400
    
    # Jeśli nie ma klucza kategorii, nie można klasyfikować
    if not job.category_key or not job.category_key.categories:
        return render_template('scraping/error.html', message="Brak klucza kategorii. Najpierw uruchom scraping i analizę."), 400
    
    # Jeśli klasyfikacja nie była jeszcze wykonana, uruchom automatycznie
    if not job.has_classification():
        # Uruchom klasyfikację w tle
        executor.submit(run_classification_all, job_id)
    
    # Przygotuj dane komentarzy dla JavaScript
    comments_data = []
    if job.scraping_results:
        for result in job.scraping_results:
            comments_data.append({
                'text': result.text or '',
                'author': result.author or 'Nieznany',
                'url': result.url or '',
                'source_type': result.source_type or 'post'
            })
    
    # Przygotuj dane kategorii
    categories_data = []
    if job.category_key and job.category_key.categories:
        categories_data = job.category_key.categories
    
    # Przygotuj istniejące wyniki klasyfikacji
    # Upewnij się, że klucze są intami dla łatwiejszego użycia w template
    existing_classifications = {}
    if job.classification_results:
        for key, value in job.classification_results.items():
            # Konwertuj klucz na int jeśli to możliwe
            try:
                int_key = int(key)
                existing_classifications[int_key] = value
            except (ValueError, TypeError):
                existing_classifications[key] = value
    
    return render_template('scraping/classification_results.html', 
                         job=job, 
                         comments_data=comments_data or [],
                         categories_data=categories_data or [],
                         existing_classifications=existing_classifications)

@scraping_bp.route('/api/classify', methods=['POST'])
def classify_comment_api():
    """API: Klasyfikuje pojedynczy komentarz i zapisuje wynik"""
    data = request.get_json()
    
    job_id = data.get('job_id')
    comment_index = data.get('comment_index')
    comment_text = data.get('comment_text', '')
    categories = data.get('categories', [])
    
    if not job_id or comment_index is None or not comment_text:
        return jsonify({"error": "Brak wymaganych danych"}), 400
    
    if not categories:
        return jsonify({"error": "Brak kategorii do klasyfikacji"}), 400
    
    try:
        job = job_storage.get(job_id)
        if not job:
            return jsonify({"error": "Zadanie nie znalezione"}), 404
        
        # Przygotuj klucz kategorii
        category_key_text = json.dumps(categories, ensure_ascii=False, indent=2)
        
        # Prompt dla klasyfikacji
        prompt = f"""Jesteś ekspertem w klasyfikacji tekstu i analizie sentymentu. Otrzymujesz klucz kategoryzacyjny oraz jeden komentarz do oceny.

<klucz_kategorii>
{category_key_text}
</klucz_kategorii>

<komentarz_do_oceny>
{comment_text}
</komentarz_do_oceny>

Wykonaj DWA zadania:
1. Przypisz komentarz do DOKŁADNIE JEDNEJ kategorii z klucza (użyj pola "aspekt").
2. Oceń sentiment (tonację emocjonalną) komentarza jako: "pozytywny", "negatywny" lub "neutralny".

Zwróć wynik w formacie JSON:
{{
  "kategoria": "nazwa_aspektu",
  "sentiment": "pozytywny/negatywny/neutralny"
}}

Nie dodawaj żadnych innych wyjaśnień, tylko czysty JSON."""
        
        # Wywołaj Gemini Flash Lite
        response = gemini_service.flash_lite_model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parsuj odpowiedź
        parsed = gemini_service.parse_json_response(response_text)
        
        if isinstance(parsed, list):
            result = parsed[0] if len(parsed) > 0 else {}
        else:
            result = parsed if isinstance(parsed, dict) else {}
        
        category = result.get('kategoria', result.get('aspekt', 'Nieznana'))
        sentiment = result.get('sentiment', 'neutralny').lower()
        
        if sentiment not in ['pozytywny', 'negatywny', 'neutralny']:
            sentiment = 'neutralny'
        
        # Zapisz wynik do zadania
        if not job.classification_results:
            job.classification_results = {}
        
        job.classification_results[int(comment_index)] = {
            'category': category,
            'sentiment': sentiment
        }
        job_storage.update(job)
        
        # Zapisz do JSON
        try:
            storage_service.save_job_to_json(job)
        except:
            pass
        
        return jsonify({
            "category": category,
            "sentiment": sentiment
        })
        
    except Exception as e:
        logger.add_log(f"Błąd klasyfikacji: {str(e)}", "ERROR")
        return jsonify({"error": str(e)}), 500

@scraping_bp.route('/api/status/<job_id>')
def get_status(job_id: str):
    """API: Status zadania (JSON)"""
    job = job_storage.get(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
        return jsonify({
            "job_id": job.job_id,
            "status": job.status,
            "current_step": job.current_step,
            "progress": job.progress,
            "results_count": len(job.scraping_results),
            "categories_count": len(job.category_key.categories) if job.category_key else 0,
            "error_message": job.error_message
        })

@scraping_bp.route('/load-from-json', methods=['POST'])
def load_from_json():
    """Wczytuje zadanie z pliku JSON"""
    data = request.get_json()
    job_id = data.get('job_id')
    
    if not job_id:
        return jsonify({"error": "Brak job_id"}), 400
    
    try:
        filepath = os.path.join(storage_service.data_dir, f"job_{job_id}.json")
        if not os.path.exists(filepath):
            return jsonify({"error": "Plik nie znaleziony"}), 404
        
        job = storage_service.load_job_from_json(filepath)
        job_storage.save(job)
        
        return jsonify({
            "success": True,
            "job_id": job.job_id,
            "brand_name": job.brand_name,
            "results_count": len(job.scraping_results)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@scraping_bp.route('/api/saved-jobs')
def get_saved_jobs():
    """API: Lista zapisanych zadań"""
    saved_jobs = storage_service.list_saved_jobs()
    return jsonify(saved_jobs)

@scraping_bp.route('/api/classify-all/<job_id>', methods=['POST'])
def classify_all_api(job_id: str):
    """API: Uruchamia klasyfikację wszystkich komentarzy"""
    job = job_storage.get(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if not job.category_key:
        return jsonify({"error": "Brak klucza kategorii"}), 400
    
    # Resetuj istniejące wyniki jeśli są
    job.classification_results = {}
    job_storage.update(job)
    
    # Uruchom klasyfikację w tle
    executor.submit(run_classification_all, job_id)
    
    return jsonify({"success": True, "message": "Klasyfikacja uruchomiona"})

@scraping_bp.route('/api/reset-classification/<job_id>', methods=['POST'])
def reset_classification_api(job_id: str):
    """API: Resetuje klasyfikację zadania"""
    job = job_storage.get(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    job.classification_results = {}
    job_storage.update(job)
    
    # Zapisz do JSON
    try:
        storage_service.save_job_to_json(job)
    except:
        pass
    
    return jsonify({"success": True, "message": "Klasyfikacja zresetowana"})

def convert_classification_results_to_list(job: ScrapingJob) -> list[ClassificationResult]:
    """Konwertuje classification_results z dict do list[ClassificationResult]"""
    results = []
    if not job.classification_results or not job.scraping_results:
        return results
    
    for idx, result in enumerate(job.scraping_results):
        if idx in job.classification_results:
            class_data = job.classification_results[idx]
            results.append(ClassificationResult(
                comment_text=result.text or "",
                category=class_data.get('category', 'Nieznana'),
                sentiment=class_data.get('sentiment', 'neutralny'),
                comment_index=idx
            ))
    
    return results

def generate_report_background(job_id: str):
    """Funkcja uruchamiana w tle: generuje raport"""
    try:
        job = job_storage.get(job_id)
        
        # Jeśli nie ma w pamięci, wczytaj z JSON
        if not job:
            try:
                filepath = os.path.join(storage_service.data_dir, f"job_{job_id}.json")
                if os.path.exists(filepath):
                    job = storage_service.load_job_from_json(filepath)
                    job_storage.save(job)
            except:
                pass
        
        if not job:
            logger.add_log(f"Nie można wygenerować raportu - zadanie {job_id} nie znalezione", "ERROR")
            return
        
        if not job.has_classification():
            logger.add_log(f"Nie można wygenerować raportu - brak klasyfikacji dla {job_id}", "WARNING")
            return
        
        if not job.category_key:
            logger.add_log(f"Nie można wygenerować raportu - brak klucza kategorii dla {job_id}", "WARNING")
            return
        
        # Konwertuj classification_results
        classification_results = convert_classification_results_to_list(job)
        
        if not classification_results:
            logger.add_log(f"Brak wyników klasyfikacji do raportu dla {job_id}", "WARNING")
            return
        
        # Generuj raport
        logger.add_log(f"Rozpoczęto generowanie raportu dla {job_id}")
        report_data = report_service.generate_report(
            classification_results=classification_results,
            category_key=job.category_key,
            brand_name=job.brand_name,
            job_id=job_id,
            start_date=job.start_date,
            end_date=job.end_date
        )
        
        logger.add_log(f"Raport wygenerowany dla {job_id}: {report_data['html']}")
        
    except Exception as e:
        logger.add_log(f"Błąd generowania raportu dla {job_id}: {str(e)}", "ERROR")

@scraping_bp.route('/api/generate-report/<job_id>', methods=['POST'])
def generate_report_api(job_id: str):
    """API: Uruchamia generowanie raportu"""
    job = job_storage.get(job_id)
    
    # Jeśli nie ma w pamięci, wczytaj z JSON
    if not job:
        try:
            filepath = os.path.join(storage_service.data_dir, f"job_{job_id}.json")
            if os.path.exists(filepath):
                job = storage_service.load_job_from_json(filepath)
                job_storage.save(job)
        except:
            pass
    
    if not job:
        return jsonify({"error": "Zadanie nie znalezione"}), 404
    
    if not job.has_classification():
        return jsonify({"error": "Brak klasyfikacji. Najpierw wykonaj klasyfikację komentarzy."}), 400
    
    if not job.category_key:
        return jsonify({"error": "Brak klucza kategorii"}), 400
    
    # Sprawdź czy raport już istnieje
    report_path = os.path.join(report_service.reports_dir, f'report_{job_id}.html')
    if os.path.exists(report_path):
        return jsonify({
            "success": True,
            "message": "Raport już istnieje",
            "report_url": url_for('scraping.view_report', job_id=job_id)
        })
    
    # Uruchom generowanie w tle
    executor.submit(generate_report_background, job_id)
    
    return jsonify({
        "success": True,
        "message": "Generowanie raportu rozpoczęte. Odśwież stronę za chwilę."
    })

@scraping_bp.route('/report/<job_id>')
def view_report(job_id: str):
    """Wyświetla raport HTML"""
    report_path = os.path.join(report_service.reports_dir, f'report_{job_id}.html')
    
    if not os.path.exists(report_path):
        # Sprawdź czy zadanie istnieje
        job = job_storage.get(job_id)
        if not job:
            try:
                filepath = os.path.join(storage_service.data_dir, f"job_{job_id}.json")
                if os.path.exists(filepath):
                    job = storage_service.load_job_from_json(filepath)
            except:
                pass
        
        if not job:
            return render_template('scraping/error.html', message="Zadanie nie znalezione"), 404
        
        if not job.has_classification():
            return render_template('scraping/error.html', 
                                message="Brak klasyfikacji. Najpierw wykonaj klasyfikację komentarzy."), 400
        
        # Raport jeszcze nie wygenerowany
        return render_template('scraping/report_generating.html', job_id=job_id, job=job)
    
    # Wczytaj i wyświetl raport
    with open(report_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Pobierz dane zadania dla kontekstu
    job = job_storage.get(job_id)
    if not job:
        try:
            filepath = os.path.join(storage_service.data_dir, f"job_{job_id}.json")
            if os.path.exists(filepath):
                job = storage_service.load_job_from_json(filepath)
        except:
            pass
    
    return render_template('scraping/report.html', 
                         report_html=html_content, 
                         job_id=job_id,
                         job=job)

@scraping_bp.route('/report/<job_id>/download')
def download_report(job_id: str):
    """Pobiera raport w formacie DOCX"""
    format_type = request.args.get('format', 'docx').lower()
    
    if format_type != 'docx':
        return jsonify({"error": "Nieprawidłowy format. Użyj: docx"}), 400
    
    # Sprawdź czy raport HTML istnieje
    html_path = os.path.join(report_service.reports_dir, f'report_{job_id}.html')
    if not os.path.exists(html_path):
        return jsonify({"error": "Raport nie został jeszcze wygenerowany"}), 404
    
    try:
        if format_type == 'docx':
            # Wczytaj markdown
            markdown_path = os.path.join(report_service.reports_dir, f'report_{job_id}.md')
            if not os.path.exists(markdown_path):
                return jsonify({"error": "Plik markdown nie znaleziony"}), 404
            
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Pobierz ścieżki wykresów
            chart_paths = {
                'bar': os.path.join(report_service.visualization_service.charts_dir, f'bar_chart_{job_id}.png'),
                'sentiment_pie': os.path.join(report_service.visualization_service.charts_dir, f'sentiment_pie_{job_id}.png'),
                'categories_pie': os.path.join(report_service.visualization_service.charts_dir, f'categories_pie_{job_id}.png')
            }
            
            docx_path = report_service.export_to_docx(markdown_content, chart_paths, job_id)
            return send_file(docx_path, as_attachment=True,
                           download_name=f'report_{job_id}.docx',
                           mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    
    except ImportError as e:
        return jsonify({"error": f"Biblioteka nie zainstalowana: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Błąd eksportu: {str(e)}"}), 500
