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
    
    // Add click handler for PDF export button
    const exportPdfBtn = document.getElementById('export-pdf');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function() {
            prepareForPrint();
        });
    }
    
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
      // Prepare timesheet for printing/PDF export with enhanced professional styling
    function prepareForPrint() {
        const timesheetContainer = document.getElementById('timesheet-container');
        if (!timesheetContainer) return;
        
        // Get timesheet title information
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0];
        const timesheet = document.getElementById('timesheet-table');
        
        // Get department and month information
        const departmentSelect = document.getElementById('department-select');
        const selectedDept = departmentSelect ? departmentSelect.options[departmentSelect.selectedIndex].text : 'All Departments';
        
        const monthSelect = document.getElementById('month-select');
        let monthName = '';
        const monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        
        if (monthSelect) {
            const monthVal = parseInt(monthSelect.value);
            monthName = monthNames[monthVal];
        }
        
        const yearSelect = document.getElementById('year-select');
        const yearVal = yearSelect ? yearSelect.value : new Date().getFullYear();
        
        // Get housing information if available
        const housingSelect = document.getElementById('housing-select');
        const selectedHousing = housingSelect ? housingSelect.options[housingSelect.selectedIndex].text : 'All Housings';
        
        // Get period dates if available
        let periodText = '';
        const timeSheetHeader = document.querySelector('.card-header .text-muted');
        if (timeSheetHeader) {
            const periodInfo = timeSheetHeader.textContent.match(/Period: ([\d/]+) - ([\d/]+)/);
            if (periodInfo && periodInfo.length >= 3) {
                periodText = `${periodInfo[1]} - ${periodInfo[2]}`;
            }
        }
        
        // Process table data to ensure it's properly formatted for printing
        // Clone the table and add proper class names
        const tableClone = timesheet.cloneNode(true);
        tableClone.classList.add('timesheet-print-table');
        tableClone.classList.remove('table-dark', 'table-hover');
        
        // Add appropriate classes to housing rows
        const housingRows = tableClone.querySelectorAll('tr.bg-secondary');
        housingRows.forEach(row => {
            row.classList.remove('bg-secondary');
            row.children[0].classList.add('housing-header');
        });
        
        // Mark weekend columns
        const headers = tableClone.querySelectorAll('thead tr:nth-child(2) th');
        headers.forEach(header => {
            const text = header.textContent.trim();
            if (text === 'Fri' || text === 'Sat') {
                const index = Array.from(headers).indexOf(header);
                const cells = tableClone.querySelectorAll(`tbody tr td:nth-child(${index + 1})`);
                cells.forEach(cell => {
                    cell.classList.add('weekend-day');
                });
                header.classList.add('weekend-day');
                const dayHeader = tableClone.querySelector(`thead tr:first-child th:nth-child(${index + 1})`);
                if (dayHeader) {
                    dayHeader.classList.add('weekend-day');
                }
            }
        });
        
        // Mark total columns
        const regularHoursHeader = tableClone.querySelector('thead tr:first-child th.bg-primary');
        if (regularHoursHeader) {
            regularHoursHeader.classList.remove('bg-primary');
            regularHoursHeader.classList.add('total-column');
        }
        
        const overtimeHeader = tableClone.querySelector('thead tr:first-child th.bg-info');
        if (overtimeHeader) {
            overtimeHeader.classList.remove('bg-info');
            overtimeHeader.classList.add('total-column');
        }
        
        // Open print dialog with professionally styled content
        const printWindow = window.open('', '_blank');
        
        // Get host URL for relative paths
        const host = window.location.protocol + '//' + window.location.host;
        
        printWindow.document.write(`
            <html>
                <head>
                    <title>Monthly Timesheet - ${monthName} ${yearVal}</title>
                    <link rel="stylesheet" href="${host}/static/css/timesheet-print.css">
                    <meta charset="UTF-8">
                </head>
                <body>
                    <div class="print-container">
                        <div class="print-header">
                            <img src="${host}/static/img/company-logo.svg" alt="Company Logo" class="logo">
                            <h1>Monthly Timesheet</h1>
                            <h2>${monthName} ${yearVal}</h2>
                            
                            <div class="info-container">
                                <div class="company-info">
                                    <div><strong>Department:</strong> ${selectedDept}</div>
                                    <div><strong>Housing:</strong> ${selectedHousing}</div>
                                    <div><strong>Period:</strong> ${periodText}</div>
                                </div>
                                <div class="timesheet-info">
                                    <div><strong>Generated:</strong> ${formattedDate}</div>
                                    <div><strong>Report ID:</strong> TS-${today.getTime().toString().substr(-6)}</div>
                                </div>
                            </div>
                        </div>
                        
                        ${tableClone.outerHTML}
                        
                        <div class="status-legend">
                            <div class="status-legend-item">
                                <div class="status-legend-color status-P"></div>
                                <div>Present (P)</div>
                            </div>
                            <div class="status-legend-item">
                                <div class="status-legend-color status-A"></div>
                                <div>Absent (A)</div>
                            </div>
                            <div class="status-legend-item">
                                <div class="status-legend-color status-V"></div>
                                <div>Vacation (V)</div>
                            </div>
                            <div class="status-legend-item">
                                <div class="status-legend-color status-S"></div>
                                <div>Sick (S)</div>
                            </div>
                            <div class="status-legend-item">
                                <div class="status-legend-color status-E"></div>
                                <div>Excused (E)</div>
                            </div>
                            <div class="status-legend-item">
                                <div class="status-legend-color status-W"></div>
                                <div>Weekend (W)</div>
                            </div>
                            <div class="status-legend-item">
                                <div class="status-legend-color status-T"></div>
                                <div>Transfer (T)</div>
                            </div>
                        </div>
                        
                        <div class="signature-section">
                            <div class="signature-box">
                                <div class="signature-line">Prepared By</div>
                            </div>
                            <div class="signature-box">
                                <div class="signature-line">Approved By</div>
                            </div>
                            <div class="signature-box">
                                <div class="signature-line">Department Manager</div>
                            </div>
                        </div>
                        
                        <div class="print-footer">
                            <div>Housing Maintenance System - Monthly Timesheet</div>
                            <div class="page-info">Page 1 of 1</div>
                        </div>
                    </div>
                    
                    <script>
                        window.onload = function() {
                            setTimeout(function() {
                                window.print();
                            }, 1000);
                        }
                    </script>
                </body>
            </html>
        `);
        
        printWindow.document.close();
        printWindow.focus();
    }
});
