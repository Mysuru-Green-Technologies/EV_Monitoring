$(document).ready(function() {
    // Load initial content
    loadContent('/dashboard-content');
    
    // Navigation handlers
    $('#dashboard-link').click(function(e) {
        e.preventDefault();
        loadContent('/dashboard-content');
    });
    
    $('#transactions-link').click(function(e) {
        e.preventDefault();
        loadContent('/transactions-content');
    });
    
    $('#reports-link').click(function(e) {
        e.preventDefault();
        loadContent('/reports-content');
    });
    
    // Filter handler
    $('#apply-filters').click(function() {
        const timeRange = $('#time-range').val();
        const chargerType = $('#charger-type').val();
        const currentPath = window.location.pathname;
        
        if (currentPath.includes('dashboard')) {
            loadContent(`/dashboard-content?range=${timeRange}&charger_type=${chargerType}`);
        } else if (currentPath.includes('transactions')) {
            loadContent(`/transactions-content?range=${timeRange}&charger_type=${chargerType}`);
        } else if (currentPath.includes('reports')) {
            loadContent(`/reports-content?range=${timeRange}&charger_type=${chargerType}`);
        }
    });
    
    function loadContent(url) {
        $.get(url, function(data) {
            $('main').html(data);
        }).fail(function() {
            alert('Failed to load content');
        });
    }
});