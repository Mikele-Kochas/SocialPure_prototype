# SocialPure Prototype - System Monitoringu i Analizy Mediów Społecznych

## 📋 Opis projektu

Zaawansowana aplikacja Flask do monitorowania i analizy komentarzy z mediów społecznych (Facebook). System automatyzuje cały proces od scrapingu danych, poprzez inteligentną klasyfikację, do generowania szczegółowych raportów analitycznych.

**Kluczowe funkcjonalności:**
- 🔍 Scraping komentarzy z Facebook (integracja Apify)
- 🤖 Inteligentna klasyfikacja komentarzy (Google Gemini API)
- 📊 Generowanie raportów analitycznych w formacie PDF/DOCX
- 📈 Wizualizacja wyników i trendów
- 🔄 Modułowa architektura umożliwiająca łatwe rozszerzenia
- 🛡️ Obsługa błędów i logging operacji

## 🏗️ Architektura projektu

```
SocialPure_prototype/
├── app.py                          # Główny plik Flask (entry point)
├── config.py                       # Konfiguracja i zmienne środowiskowe
├── requirements.txt                # Zależności projektu
├── .env.example                    # Szablon zmiennych środowiskowych
│
├── models/                         # Modele danych
│   ├── scraping_job.py            # Model zadania scrapingu
│   ├── scraping_result.py         # Model wyniku scrapingu
│   ├── category_key.py            # Model klucza kategorii
│   └── classification_result.py   # Model wyniku klasyfikacji
│
├── services/                       # Logika biznesowa - orchestration
│   ├── scraping_orchestrator.py   # Koordynacja procesu scrapingu
│   ├── classification_orchestrator.py # Koordynacja klasyfikacji
│   ├── apify_service.py           # Integracja z Apify API
│   ├── facebook_scraper.py        # Scraper Facebook (Apify Actor)
│   ├── facebook_search.py         # Wyszukiwanie na Facebook
│   ├── query_generator.py         # Generowanie zapytań wyszukiwania
│   ├── gemini_service.py          # Integracja z Google Gemini
│   ├── report_service.py          # Generowanie raportów
│   ├── visualization_service.py   # Tworzenie wizualizacji
│   ├── workflow_orchestrator.py   # Główny orchestrator przepływu
│   ├── job_storage.py             # Przechowywanie statusu zadań
│   ├── storage_service.py         # Obsługa przechowywania danych
│   └── logger.py                  # System logowania
│
├── blueprints/                     # Flask blueprints - routy i endpoints
│   ├── scraping.py                # Główne endpointy aplikacji
│   └── api.py                     # API endpoints
│
├── utils/                          # Narzędzia pomocnicze
│   ├── helpers.py                 # Funkcje pomocnicze
│   └── validators.py              # Walidacja danych wejściowych
│
├── templates/                      # Szablony HTML
│   ├── base.html                  # Szablon bazowy
│   └── scraping/                  # Szablony widoków
│       ├── index.html             # Strona główna
│       ├── classification.html    # Widok klasyfikacji
│       ├── classification_results.html # Wyniki klasyfikacji
│       ├── results.html           # Wyniki scrapingu
│       ├── logs.html              # Logi systemu
│       └── error.html             # Strona błędu
│
├── static/                         # Pliki statyczne
│   ├── css/
│   │   └── style.css              # Stylizacja
│   └── js/
│       ├── main.js                # Skrypty główne
│       └── classification.js      # Skrypty klasyfikacji
│
└── data/                           # Przechowywanie wyników zadań
```

## 🚀 Szybki start

### Wymagania
- Python 3.9+
- pip

### Instalacja

1. **Sklonuj repozytorium:**
   ```bash
   git clone https://github.com/Mikele-Kochas/SocialPure_prototype.git
   cd SocialPure_prototype
   ```

2. **Zainstaluj zależności:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Skonfiguruj zmienne środowiskowe:**
   ```bash
   cp .env.example .env
   ```
   Edytuj `.env` i uzupełnij:
   - `APIFY_API_TOKEN` - token z https://apify.com
   - `GEMINI_API_KEY` - klucz API z https://aistudio.google.com

4. **Uruchom aplikację:**
   ```bash
   python app.py
   ```
   Aplikacja będzie dostępna pod adresem `http://127.0.0.1:5000`

## 📊 Przepływ pracy

```
1. Użytkownik wprowadza dane (marka, daty)
         ↓
2. System uruchamia scraping Facebook (Apify Actor)
         ↓
3. System generuje klucz kategorii (Gemini Flash)
         ↓
4. System klasyfikuje komentarze (Gemini Flash Lite)
         ↓
5. System generuje raport i wizualizacje (Gemini Flash)
         ↓
6. Użytkownik przegląda wyniki w interfejsie webowym
```

## 🔑 Komponenty systemu

### 1. **Scraping Module**
- Wyszukiwanie wzmianek marki na Facebook
- Zbieranie komentarzy z postów, grup, wydarzeń
- Ekstrakcja metadanych (autorzy, czasy, oddziaływanie)

### 2. **Classification Module**
- Generowanie inteligentnego klucza kategorii na podstawie komentarzy
- Klasyfikacja każdego komentarza do odpowiedniej kategorii
- Wsparcie dla sentimentu i intent analysis

### 3. **Report Module**
- Generowanie raportów w PDF/DOCX
- Podsumowanie ilościowe i jakościowe
- Rekomendacje na podstawie analizy

### 4. **Visualization Module**
- Wykresy trendów
- Mapy ciepła kategorii
- Diagramy sentimentu

## 📦 Zależności

**Główne biblioteki:**
- **Flask 3.0+** - framework webowy
- **google-generativeai** - API Google Gemini
- **apify-client** - klient Apify
- **pandas** - analiza danych
- **matplotlib** - wizualizacje
- **python-docx, xhtml2pdf** - generowanie raportów

Pełna lista w `requirements.txt`

## ⚙️ Konfiguracja

### Zmienne środowiskowe (.env)
```
# API Keys (WYMAGANE)
APIFY_API_TOKEN=your_token_here
GEMINI_API_KEY=your_key_here

# Flask Configuration
SECRET_KEY=your-secret-key
DEBUG=False

# Limity
MAX_RESULTS=20
MAX_ACTOR_RESULTS=100
SCRAPING_TIMEOUT=300
```

## 🎯 Główne endpointy

- `GET /` - Strona główna
- `POST /scrape` - Uruchamia scraping
- `GET /results/<job_id>` - Wyniki scrapingu
- `POST /classify` - Uruchamia klasyfikację
- `GET /classification_results/<job_id>` - Wyniki klasyfikacji
- `GET /logs` - Logi systemu
- `GET /report/<job_id>` - Pobieranie raportu

## 🔍 Rozwiązywanie problemów

### Błąd: "APIFY_API_TOKEN nie jest ustawiony"
- Upewnij się, że `.env` zawiera prawidłowy token
- Plik `.env` powinien być w głównym katalogu projektu

### Błąd podczas scrapingu
- Sprawdź połączenie internetowe
- Weryfikuj limit API Apify
- Sprawdź logi w `/logs`

## 📝 Licencja

MIT License - patrz plik LICENSE

## 👤 Autor

Mikele-Kochas


---

**Status:** Prototype (w aktywnym rozwoju)

