// Zmienne globalne
let globalCategories = [];

// Klasyfikacja komentarzy - GLOBALNA ZMIENNA
let classificationData = {
    results: {},
    stats: {
        categories: {},
        sentiment: { pozytywny: 0, neutralny: 0, negatywny: 0 }
    }
};

// Instancje wykresów Chart.js
let sentimentChartInstance = null;
let categoriesChartInstance = null;

// Funkcja inicjalizacji danych (wywoływana z HTML)
function initializeClassificationData(existingClassifications, categoriesList) {
    console.log('initializeClassificationData wywołana');
    console.log('existingClassifications:', existingClassifications);
    console.log('categoriesList:', categoriesList);
    
    // Zapisz kategorie globalnie
    globalCategories = categoriesList || [];
    console.log('globalCategories ustawione na:', globalCategories);
    
    // Wczytaj istniejące wyniki klasyfikacji
    if (existingClassifications && Object.keys(existingClassifications).length > 0) {
        Object.keys(existingClassifications).forEach(index => {
            const result = existingClassifications[index];
            const idx = parseInt(index);
            classificationData.results[idx] = result;
            
            // Aktualizuj statystyki
            if (result && result.category) {
                classificationData.stats.categories[result.category] = 
                    (classificationData.stats.categories[result.category] || 0) + 1;
            }
            if (result && result.sentiment) {
                classificationData.stats.sentiment[result.sentiment] = 
                    (classificationData.stats.sentiment[result.sentiment] || 0) + 1;
            }
        });
    }
    
    // Inicjalizacja statystyk kategorii - upewnij się, że wszystkie kategorie mają wpis (nawet z 0)
    if (categoriesList && categoriesList.length > 0) {
        categoriesList.forEach((cat) => {
            // Obsługa różnych formatów danych kategorii
            let categoryName = '';
            if (typeof cat === 'string') {
                categoryName = cat;
            } else if (cat && typeof cat === 'object') {
                categoryName = cat.aspekt || cat['aspekt'] || '';
            }
            
            if (categoryName) {
                // Zainicjalizuj kategorię z 0 jeśli jeszcze nie istnieje
                if (!(categoryName in classificationData.stats.categories)) {
                    classificationData.stats.categories[categoryName] = 0;
                }
            }
        });
    }
    
    console.log('Po inicjalizacji - classificationData.stats:', classificationData.stats);
}

// Funkcja klasyfikacji pojedynczego komentarza
async function classifyComment(commentIndex) {
    const comment = comments[commentIndex];
    const commentElement = document.querySelector(`[data-comment-id="${commentIndex}"]`);
    const resultElement = document.getElementById(`result-${commentIndex}`);
    
    if (!comment || !commentElement || !resultElement) return;
    
    // Pokaż loading
    resultElement.innerHTML = '<em>Klasyfikowanie...</em>';
    commentElement.classList.add('classifying');
    
    try {
        const response = await fetch('/api/classify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                job_id: jobId,
                comment_index: commentIndex,
                comment_text: comment.text || comment.comment_text || '',
                categories: categories
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            resultElement.innerHTML = `<span style="color: red;">Błąd: ${data.error}</span>`;
            return;
        }
        
        // Zapisz wynik
        classificationData.results[commentIndex] = data;
        
        // Aktualizuj statystyki
        if (data.category) {
            classificationData.stats.categories[data.category] = 
                (classificationData.stats.categories[data.category] || 0) + 1;
        }
        if (data.sentiment) {
            classificationData.stats.sentiment[data.sentiment] += 1;
        }
        
        // Wyświetl wynik
        displayClassificationResult(commentIndex, {
            category: data.category,
            sentiment: data.sentiment
        });
        updateCharts();
        
        commentElement.classList.remove('classifying');
        commentElement.classList.add('classified');
        
    } catch (error) {
        resultElement.innerHTML = `<span style="color: red;">Błąd: ${error.message}</span>`;
        commentElement.classList.remove('classifying');
    }
}

// Wyświetl wynik klasyfikacji
function displayClassificationResult(commentIndex, data) {
    const resultElement = document.getElementById(`result-${commentIndex}`);
    
    const categoryClass = 'category';
    const sentimentClass = `sentiment sentiment-${data.sentiment || 'neutralny'}`;
    const sentimentText = data.sentiment === 'pozytywny' ? '😊 Pozytywny' : 
                         data.sentiment === 'negatywny' ? '😞 Negatywny' : 
                         '😐 Neutralny';
    
    resultElement.innerHTML = `
        <span class="${categoryClass}">${data.category || 'Nieznana'}</span>
        <span class="${sentimentClass}">${sentimentText}</span>
    `;
}

// Aktualizuj wykresy
function updateCharts() {
    updateSentimentChart();
    updateCategoriesChart();
}

// Aktualizuj wykres sentymentu (Chart.js)
function updateSentimentChart() {
    const canvas = document.getElementById('sentimentChart');
    if (!canvas) return;
    
    const stats = classificationData.stats.sentiment;
    const total = stats.pozytywny + stats.neutralny + stats.negatywny;
    
    const data = {
        labels: ['Pozytywny', 'Neutralny', 'Negatywny'],
        datasets: [{
            data: [stats.pozytywny, stats.neutralny, stats.negatywny],
            backgroundColor: ['#28a745', '#6c757d', '#dc3545'],
            borderWidth: 2,
            borderColor: '#fff'
        }]
    };
    
    const config = {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };
    
    if (sentimentChartInstance) {
        sentimentChartInstance.data = data;
        sentimentChartInstance.update();
    } else {
        sentimentChartInstance = new Chart(canvas, config);
    }
}

// Aktualizuj wykres kategorii (Chart.js)
function updateCategoriesChart() {
    const canvas = document.getElementById('categoriesChart');
    if (!canvas) {
        console.warn('Canvas categoriesChart nie znaleziony');
        return;
    }
    
    const stats = classificationData.stats.categories;
    
    // Debug - sprawdź co mamy w statystykach
    console.log('updateCategoriesChart - Statystyki kategorii:', stats);
    
    // Pobierz wszystkie kategorie (nawet z zerami)
    const allEntries = Object.entries(stats);
    const entriesWithData = allEntries.filter(([_, count]) => count > 0);
    
    console.log('Wszystkie wpisy:', allEntries);
    console.log('Wpisy z liczbą > 0:', entriesWithData);
    
    // Jeśli nie ma żadnych kategorii w statystykach, użyj kategorii z listy
    let labels, values;
    if (allEntries.length === 0 && globalCategories && globalCategories.length > 0) {
        // Użyj kategorii z listy i ustaw wszystkie na 0
        labels = globalCategories.map(cat => {
            if (typeof cat === 'string') return cat;
            return cat.aspekt || cat['aspekt'] || 'Nieznana';
        }).filter(name => name);
        values = new Array(labels.length).fill(0);
        console.log('Używam kategorii z listy (globalCategories):', labels);
    } else if (allEntries.length > 0) {
        // Użyj wszystkich kategorii ze statystyk (nawet z zerami)
        labels = allEntries.map(([category, _]) => category);
        values = allEntries.map(([_, count]) => count);
    } else {
        // Brak danych - pokaż komunikat
        labels = ['Brak danych'];
        values = [0];
    }
    
    const data = {
        labels: labels,
        datasets: [{
            label: 'Liczba komentarzy',
            data: values,
            backgroundColor: '#667eea',
            borderColor: '#5568d3',
            borderWidth: 2
        }]
    };
    
    const config = {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Liczba: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: {
                            size: 11
                        }
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        font: {
                            size: 10
                        },
                        padding: 5,
                        callback: function(value, index, ticks) {
                            const label = this.getLabelForValue(value);
                            // Skróć długie etykiety do maksymalnie 20 znaków
                            if (label && label.length > 20) {
                                return label.substring(0, 17) + '...';
                            }
                            return label;
                        }
                    }
                }
            },
            layout: {
                padding: {
                    bottom: 40,
                    top: 10,
                    left: 10,
                    right: 10
                }
            }
        }
    };
    
    if (categoriesChartInstance) {
        categoriesChartInstance.data = data;
        categoriesChartInstance.update();
    } else {
        categoriesChartInstance = new Chart(canvas, config);
    }
}

// Klasyfikuj wszystkie komentarze
async function classifyAll() {
    const btn = document.getElementById('classifyAllBtn');
    if (btn.disabled) return;
    
    btn.disabled = true;
    btn.textContent = 'Klasyfikowanie...';
    
    for (let i = 0; i < comments.length; i++) {
        await classifyComment(i);
        // Małe opóźnienie między requestami
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    btn.disabled = false;
    btn.textContent = '✅ Wszystkie sklasyfikowane';
}

// Resetuj klasyfikację
async function resetClassification() {
    if (!confirm('Czy na pewno chcesz zresetować klasyfikację i uruchomić ją ponownie?')) {
        return;
    }
    
    try {
        // Resetuj na serwerze
        const response = await fetch(`/api/reset-classification/${jobId}`, { method: 'POST' });
        const data = await response.json();
        
        if (!data.success) {
            alert('Błąd resetowania klasyfikacji');
            return;
        }
        
        // Wyczyść lokalne dane
        classificationData = {
            results: {},
            stats: {
                categories: {},
                sentiment: { pozytywny: 0, neutralny: 0, negatywny: 0 }
            }
        };
        
        categories.forEach((cat) => {
            classificationData.stats.categories[cat.aspekt] = 0;
        });
        
        // Wyczyść wyniki w UI
        comments.forEach((_, index) => {
            const resultElement = document.getElementById(`result-${index}`);
            if (resultElement) {
                resultElement.innerHTML = '<em>Klasyfikowanie...</em>';
            }
            const commentElement = document.querySelector(`[data-comment-id="${index}"]`);
            if (commentElement) {
                commentElement.classList.remove('classified', 'classifying');
            }
        });
        
        updateCharts();
        
        // Uruchom ponownie klasyfikację wszystkich
        const classifyResponse = await fetch(`/api/classify-all/${jobId}`, { method: 'POST' });
        if (classifyResponse.ok) {
            // Odśwież stronę po chwili
            setTimeout(() => location.reload(), 1000);
        }
    } catch (error) {
        console.error('Błąd resetowania:', error);
        alert('Błąd resetowania klasyfikacji');
    }
}

// Auto-refresh dla klasyfikacji w toku
function checkClassificationStatus() {
    fetch(`/api/classification-status/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) return;
            
            // Jeśli klasyfikacja się zakończyła, zaktualizuj wyniki
            if (data.has_classification && data.status === 'completed') {
                // Zaktualizuj wyniki które jeszcze nie są wyświetlone
                Object.keys(data.classification_results).forEach(index => {
                    const idx = parseInt(index);
                    if (!classificationData.results[idx]) {
                        const result = data.classification_results[index];
                        classificationData.results[idx] = result;
                        displayClassificationResult(idx, result);
                        
                        // Aktualizuj statystyki
                        if (result.category) {
                            classificationData.stats.categories[result.category] = 
                                (classificationData.stats.categories[result.category] || 0) + 1;
                        }
                        if (result.sentiment) {
                            classificationData.stats.sentiment[result.sentiment] += 1;
                        }
                    }
                });
                
                updateCharts();
            }
        })
        .catch(error => console.error('Błąd sprawdzania statusu:', error));
}

// Funkcja inicjalizacji UI (wywoływana po załadowaniu danych)
function initializeUI(existingClassificationsData, commentsData) {
    // Wyświetl istniejące wyniki klasyfikacji
    if (existingClassificationsData && Object.keys(existingClassificationsData).length > 0) {
        Object.keys(existingClassificationsData).forEach(index => {
            const idx = parseInt(index);
            const result = existingClassificationsData[index];
            if (result && typeof displayClassificationResult === 'function') {
                displayClassificationResult(idx, result);
                const commentElement = document.querySelector(`[data-comment-id="${idx}"]`);
                if (commentElement) {
                    commentElement.classList.add('classified');
                }
            }
        });
    }
    
    // Zaktualizuj wykresy na początku
    if (typeof updateCharts === 'function') {
        updateCharts();
    }
    
    // Auto-refresh jeśli klasyfikacja w toku
    const totalComments = commentsData ? commentsData.length : 0;
    const classifiedCount = existingClassificationsData ? Object.keys(existingClassificationsData).length : 0;
    const hasAllClassifications = classifiedCount === totalComments && totalComments > 0;
    
    if (!hasAllClassifications && typeof jobId !== 'undefined') {
        const refreshInterval = setInterval(() => {
            if (typeof checkClassificationStatus === 'function') {
                checkClassificationStatus();
            }
            // Sprawdź czy wszystkie są sklasyfikowane
            fetch(`/api/classification-status/${jobId}`)
                .then(r => r.json())
                .then(data => {
                    if (data.classification_count === data.total_comments && data.status === 'completed') {
                        clearInterval(refreshInterval);
                        location.reload(); // Odśwież stronę gdy zakończone
                    }
                })
                .catch(err => console.error('Błąd sprawdzania statusu:', err));
        }, 3000); // Co 3 sekundy
    }
    
    // Kliknięcie w komentarz - klasyfikuj (tylko jeśli jeszcze nie sklasyfikowany)
    document.querySelectorAll('.comment-item-classification').forEach((element, index) => {
        element.addEventListener('click', () => {
            if (!classificationData.results[index] && typeof classifyComment === 'function') {
                classifyComment(index);
            }
        });
    });
    
    // Przyciski reset
    const resetBtn = document.getElementById('resetBtn');
    const resetBtnBottom = document.getElementById('resetBtnBottom');
    if (resetBtn && typeof resetClassification === 'function') {
        resetBtn.addEventListener('click', resetClassification);
    }
    if (resetBtnBottom && typeof resetClassification === 'function') {
        resetBtnBottom.addEventListener('click', resetClassification);
    }
}

// Auto-inicjalizacja gdy classification.js się załaduje
console.log('classification.js załadowany');
if (typeof window !== 'undefined') {
    window.addEventListener('load', function() {
        console.log('window load event - sprawdzam czy można zainicjalizować');
        // Sprawdź czy zmienne globalne są dostępne
        if (typeof existingClassifications !== 'undefined' && typeof categories !== 'undefined') {
            console.log('Zmienne globalne dostępne - inicjalizuję');
            if (typeof initializeClassificationData === 'function') {
                initializeClassificationData(existingClassifications, categories);
            }
            if (typeof initializeUI === 'function') {
                initializeUI(existingClassifications, comments);
            }
        }
    });
}

