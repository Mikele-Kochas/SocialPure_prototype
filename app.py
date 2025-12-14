import sys
import os
from flask import Flask

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEBUG, SECRET_KEY
from blueprints.scraping import scraping_bp

# Prawidłowa konfiguracja Flask z ścieżkami do folderu static i templates
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    static_url_path='/static'
)

app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG

# Rejestracja blueprintów
app.register_blueprint(scraping_bp)

# Debug route do sprawdzenia static files
@app.route('/debug')
def debug():
    import os
    static_path = app.static_folder
    css_path = os.path.join(static_path, 'css', 'style.css')
    js_path = os.path.join(static_path, 'js', 'main.js')
    
    return f"""
    Static folder: {static_path}<br>
    CSS exists: {os.path.exists(css_path)}<br>
    JS exists: {os.path.exists(js_path)}<br>
    CSS size: {os.path.getsize(css_path) if os.path.exists(css_path) else 'N/A'} bytes<br>
    """

@app.errorhandler(404)
def not_found(error):
    return "Strona nie znaleziona", 404

@app.errorhandler(500)
def internal_error(error):
    return "Wystąpił błąd serwera", 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=DEBUG)
