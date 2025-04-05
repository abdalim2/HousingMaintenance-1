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
