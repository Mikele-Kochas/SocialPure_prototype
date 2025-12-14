// Auto-refresh dla statusu zadania
function setupAutoRefresh(jobId) {
    if (!jobId) return;
    
    const refreshInterval = setInterval(function() {
        fetch(`/api/status/${jobId}`)
            .then(response => response.json())
            .then(data => {
                // Aktualizuj progress bar
                const progressBar = document.querySelector('.progress-fill');
                const progressText = document.querySelector('.progress-text');
                
                if (progressBar) {
                    progressBar.style.width = (data.progress * 100) + '%';
                }
                
                if (progressText) {
                    progressText.textContent = Math.round(data.progress * 100) + '% - ' + data.current_step;
                }
                
                // Jeśli zakończone, odśwież stronę
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(refreshInterval);
                    setTimeout(() => location.reload(), 1000);
                }
            })
            .catch(error => {
                console.error('Błąd pobierania statusu:', error);
            });
    }, 5000); // Co 5 sekund
}

// Inicjalizacja po załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    // Sprawdź czy jesteśmy na stronie wyników
    const jobIdMatch = window.location.pathname.match(/\/results\/([a-f0-9-]+)/);
    if (jobIdMatch) {
        setupAutoRefresh(jobIdMatch[1]);
    }
});
