/**
 * Timesheet functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips for attendance cells
    const attendanceCells = document.querySelectorAll('.attendance-cell');
    
    attendanceCells.forEach(cell => {
        // Add hover tooltip with attendance details
        if (cell.dataset.details) {
            new bootstrap.Tooltip(cell, {
                title: cell.dataset.details,
                placement: 'top'
            });
        }
        
        // Add click handler to show detailed information
        cell.addEventListener('click', function() {
            if (this.dataset.empId && this.dataset.date) {
                showAttendanceDetails(this.dataset.empId, this.dataset.date);
            }
        });
    });
    
    // Function to show attendance details modal
    function showAttendanceDetails(employeeId, date) {
        // In a real implementation, this would fetch attendance details from the server
        console.log(`Show attendance details for employee ${employeeId} on ${date}`);
        
        // For demonstration purposes, we'll show an alert
        alert(`Attendance details for employee ${employeeId} on ${date} would be shown in a modal`);
    }
    
    // Get configured month dates from settings - check both server-provided data and localStorage
    function getMonthDateConfig(month) {
        // First check if the server provided month_dates in the window object
        if (window.monthDatesConfig && month in window.monthDatesConfig) {
            return {
                start: window.monthDatesConfig[month].start,
                end: window.monthDatesConfig[month].end
            };
        }
        
        // Fall back to localStorage if server data is not available
        const savedMonthDates = localStorage.getItem('month_dates_config');
        if (!savedMonthDates) return null;
        
        try {
            const monthDates = JSON.parse(savedMonthDates);
            if (month in monthDates) {
                return {
                    start: monthDates[month].start,
                    end: monthDates[month].end
                };
            }
        } catch (error) {
            console.error('Error parsing saved month dates:', error);
        }
        
        return null;
    }
    
    // Initialize timesheet filter form with configured dates
    const form = document.getElementById('timesheet-filter-form');
    if (form) {
        const monthSelect = document.getElementById('month-select');
        if (monthSelect) {
            monthSelect.addEventListener('change', function() {
                const selectedMonth = this.value;
                const monthConfig = getMonthDateConfig(selectedMonth);
                
                // Update hidden fields with configured dates if available
                if (monthConfig && monthConfig.start && monthConfig.end) {
                    console.log(`Found config for month ${selectedMonth}:`, monthConfig);
                    
                    const hiddenStartInput = document.getElementById('config-start-date') || document.createElement('input');
                    hiddenStartInput.type = 'hidden';
                    hiddenStartInput.id = 'config-start-date';
                    hiddenStartInput.name = 'start_date';
                    hiddenStartInput.value = monthConfig.start;
                    
                    const hiddenEndInput = document.getElementById('config-end-date') || document.createElement('input');
                    hiddenEndInput.type = 'hidden';
                    hiddenEndInput.id = 'config-end-date';
                    hiddenEndInput.name = 'end_date';
                    hiddenEndInput.value = monthConfig.end;
                    
                    if (!document.getElementById('config-start-date')) {
                        form.appendChild(hiddenStartInput);
                    }
                    if (!document.getElementById('config-end-date')) {
                        form.appendChild(hiddenEndInput);
                    }
                } else {
                    console.log(`No config found for month ${selectedMonth}`);
                    // Remove config inputs if not available
                    const startInput = document.getElementById('config-start-date');
                    const endInput = document.getElementById('config-end-date');
                    if (startInput) startInput.remove();
                    if (endInput) endInput.remove();
                }
            });
            
            // Trigger change event on load to set initial values
            monthSelect.dispatchEvent(new Event('change'));
        }
        
        // Handle form submission
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const year = document.getElementById('year-select').value;
            const month = document.getElementById('month-select').value;
            const department = document.getElementById('department-select').value;
            
            let url = `${form.getAttribute('data-action') || '{{ url_for("timesheet") }}'}?year=${year}&month=${month}`;
            
            // Add configured dates if available
            const configStart = document.getElementById('config-start-date');
            const configEnd = document.getElementById('config-end-date');
            
            if (configStart && configStart.value) {
                url += `&start_date=${configStart.value}`;
            }
            if (configEnd && configEnd.value) {
                url += `&end_date=${configEnd.value}`;
            }
            
            if (department) {
                url += `&department=${department}`;
            }
            
            console.log('Navigating to:', url);
            window.location.href = url;
        });
    }
    
    // Handle export to various formats
    document.getElementById('export-pdf')?.addEventListener('click', function() {
        prepareForPrint();
        // In a real implementation, this would trigger a PDF generation on the backend
    });
    
    // Prepare timesheet for printing/PDF export
    function prepareForPrint() {
        const timesheetContainer = document.getElementById('timesheet-container');
        if (!timesheetContainer) return;
        
        // Create a clone of the timesheet for printing
        const printContent = timesheetContainer.cloneNode(true);
        
        // Add any specific styling or modifications needed for print
        
        // Open print dialog
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Timesheet</title>
                    <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
                    <style>
                        body { padding: 20px; }
                        .timesheet-table { width: 100%; border-collapse: collapse; }
                        .timesheet-table th, .timesheet-table td { 
                            border: 1px solid #dee2e6; 
                            padding: 8px;
                            text-align: center;
                        }
                        .status-P { background-color: rgba(40, 167, 69, 0.1); }
                        .status-A { background-color: rgba(220, 53, 69, 0.1); }
                        .status-V { background-color: rgba(40, 167, 69, 0.2); }
                        .status-T { background-color: rgba(13, 110, 253, 0.1); }
                        .status-S { background-color: rgba(255, 193, 7, 0.1); }
                        .status-E { background-color: rgba(13, 202, 240, 0.1); }
                        .status-W { background-color: rgba(108, 117, 125, 0.1); }
                        @media print {
                            body { -webkit-print-color-adjust: exact; }
                        }
                    </style>
                </head>
                <body>
                    <h2>Monthly Timesheet</h2>
                    ${printContent.innerHTML}
                </body>
            </html>
        `);
        
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
        printWindow.close();
    }
});
