"""
Serwis generowania wizualizacji - wykresy matplotlib
"""
import sys
import os
import matplotlib
matplotlib.use('Agg')  # Backend bez GUI
import matplotlib.pyplot as plt
from typing import List, Dict
from collections import Counter

# Dodaj ścieżkę do projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.classification_result import ClassificationResult

class VisualizationService:
    """Serwis generowania wykresów dla raportów"""
    
    def __init__(self):
        self.charts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'charts')
        os.makedirs(self.charts_dir, exist_ok=True)
    
    def generate_bar_chart(self, classification_results: List[ClassificationResult], job_id: str) -> str:
        """
        Generuje wykres słupkowy: kategorie × sentiment
        Zwraca ścieżkę do pliku PNG
        """
        # Przygotuj dane
        data = self._prepare_category_sentiment_data(classification_results)
        
        if not data:
            return None
        
        # Przygotuj dane do wykresu
        categories = list(data.keys())
        sentiments = ['pozytywny', 'neutralny', 'negatywny']
        colors = {'pozytywny': '#4CAF50', 'neutralny': '#9E9E9E', 'negatywny': '#F44336'}
        
        # Pozycje na osi X
        x = range(len(categories))
        width = 0.25
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for i, sentiment in enumerate(sentiments):
            values = [data[cat].get(sentiment, 0) for cat in categories]
            offset = (i - 1) * width
            ax.bar([xi + offset for xi in x], values, width, 
                   label=sentiment.capitalize(), color=colors[sentiment])
        
        ax.set_xlabel('Kategorie', fontsize=12)
        ax.set_ylabel('Liczba komentarzy', fontsize=12)
        ax.set_title('Rozkład sentymentu w kategoriach', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        # Zapisz
        filepath = os.path.join(self.charts_dir, f'bar_chart_{job_id}.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_pie_chart_sentiment(self, classification_results: List[ClassificationResult], job_id: str) -> str:
        """
        Generuje wykres kołowy rozkładu sentymentu
        Zwraca ścieżkę do pliku PNG
        """
        data = self._prepare_sentiment_data(classification_results)
        
        if not data or sum(data.values()) == 0:
            return None
        
        # Kolory
        colors = {'pozytywny': '#4CAF50', 'neutralny': '#9E9E9E', 'negatywny': '#F44336'}
        labels = [sent.capitalize() for sent in data.keys()]
        sizes = list(data.values())
        chart_colors = [colors[sent] for sent in data.keys()]
        
        fig, ax = plt.subplots(figsize=(8, 8))
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=chart_colors,
                                          autopct='%1.1f%%', startangle=90,
                                          textprops={'fontsize': 12})
        
        # Podkreśl największy segment
        if wedges:
            wedges[0].set_edgecolor('white')
            wedges[0].set_linewidth(2)
        
        ax.set_title('Rozkład sentymentu', fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # Zapisz
        filepath = os.path.join(self.charts_dir, f'sentiment_pie_{job_id}.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_pie_chart_categories(self, classification_results: List[ClassificationResult], job_id: str) -> str:
        """
        Generuje wykres kołowy rozkładu kategorii
        Zwraca ścieżkę do pliku PNG
        """
        data = self._prepare_category_data(classification_results)
        
        if not data or sum(data.values()) == 0:
            return None
        
        # Sortuj według wartości (malejąco)
        sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
        
        # Ogranicz do top 8 kategorii, reszta jako "Inne"
        if len(sorted_data) > 8:
            top_8 = dict(list(sorted_data.items())[:8])
            others_count = sum(list(sorted_data.values())[8:])
            top_8['Inne'] = others_count
            sorted_data = top_8
        
        labels = list(sorted_data.keys())
        sizes = list(sorted_data.values())
        
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Kolory - użyj palety matplotlib
        colors = plt.cm.Set3(range(len(labels)))
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                          autopct='%1.1f%%', startangle=90,
                                          textprops={'fontsize': 10})
        
        ax.set_title('Rozkład kategorii', fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # Zapisz
        filepath = os.path.join(self.charts_dir, f'categories_pie_{job_id}.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_all_charts(self, classification_results: List[ClassificationResult], job_id: str) -> Dict[str, str]:
        """
        Generuje wszystkie wykresy
        Zwraca dict: {"bar": path, "sentiment_pie": path, "categories_pie": path}
        """
        charts = {}
        
        try:
            charts['bar'] = self.generate_bar_chart(classification_results, job_id)
        except Exception as e:
            print(f"Błąd generowania wykresu słupkowego: {e}")
            charts['bar'] = None
        
        try:
            charts['sentiment_pie'] = self.generate_pie_chart_sentiment(classification_results, job_id)
        except Exception as e:
            print(f"Błąd generowania wykresu kołowego sentymentu: {e}")
            charts['sentiment_pie'] = None
        
        try:
            charts['categories_pie'] = self.generate_pie_chart_categories(classification_results, job_id)
        except Exception as e:
            print(f"Błąd generowania wykresu kołowego kategorii: {e}")
            charts['categories_pie'] = None
        
        return charts
    
    def _prepare_sentiment_data(self, classification_results: List[ClassificationResult]) -> Dict[str, int]:
        """Przygotowuje dane do wykresu sentymentu"""
        sentiment_counts = Counter()
        for result in classification_results:
            sentiment_counts[result.sentiment] += 1
        
        return dict(sentiment_counts)
    
    def _prepare_category_data(self, classification_results: List[ClassificationResult]) -> Dict[str, int]:
        """Przygotowuje dane do wykresu kategorii"""
        category_counts = Counter()
        for result in classification_results:
            category_counts[result.category] += 1
        
        return dict(category_counts)
    
    def _prepare_category_sentiment_data(self, classification_results: List[ClassificationResult]) -> Dict[str, Dict[str, int]]:
        """Przygotowuje dane do wykresu słupkowego"""
        data = {}
        for result in classification_results:
            if result.category not in data:
                data[result.category] = {'pozytywny': 0, 'neutralny': 0, 'negatywny': 0}
            data[result.category][result.sentiment] += 1
        
        return data
