/**
 * Main JavaScript functionality for Attendance Tracking System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Function to format dates
    window.formatDate = function(dateString) {
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    };
    
    // Function to format times
    window.formatTime = function(timeString) {
        const options = { hour: '2-digit', minute: '2-digit' };
        return new Date(timeString).toLocaleTimeString(undefined, options);
    };
    
    // Handle dark mode toggle if needed
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.documentElement.setAttribute('data-bs-theme', 
                document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark'
            );
        });
    }
    
    // Sync status indicator
    updateSyncStatus();
    
    // Update sync status periodically
    setInterval(updateSyncStatus, 60000); // Check every minute
    
    function updateSyncStatus() {
        const syncStatusElement = document.getElementById('sync-status');
        if (!syncStatusElement) return;
        
        // In a real implementation, this would check the status from the server
        // For demo, we'll just update the UI with a simulated status
        
        // Simulate a random status (success/warning/error)
        const statuses = ['success', 'success', 'success', 'warning', 'danger'];
        const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
        
        const messages = {
            'success': 'Connected',
            'warning': 'Sync Pending',
            'danger': 'Connection Error'
        };
        
        const icons = {
            'success': 'fas fa-sync-alt',
            'warning': 'fas fa-clock',
            'danger': 'fas fa-exclamation-triangle'
        };
        
        syncStatusElement.innerHTML = `
            <span class="badge bg-${randomStatus} me-2"><i class="${icons[randomStatus]}"></i></span>
            <span>${messages[randomStatus]}</span>
        `;
    }
    
    // Handle form submissions to prevent page reload during demo
    const demoForms = document.querySelectorAll('form.demo-form');
    demoForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            alert('Form submission would be processed on the server');
        });
    });
});
