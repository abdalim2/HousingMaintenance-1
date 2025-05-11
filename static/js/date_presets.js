/**
 * Date presets functionality for sync date selection
 */
document.addEventListener('DOMContentLoaded', function() {
    // Date preset buttons
    var datePresetBtns = document.querySelectorAll('.date-preset');
    datePresetBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var preset = this.getAttribute('data-preset');
            var startDateInput = document.getElementById('start_date');
            var endDateInput = document.getElementById('end_date');
            var customMonthSelector = document.getElementById('custom-month-selector');

            // Reset all buttons to outline style
            datePresetBtns.forEach(function(b) {
                b.classList.remove('btn-primary');
                b.classList.add('btn-outline-primary');
            });

            // Set this button to solid style
            this.classList.remove('btn-outline-primary');
            this.classList.add('btn-primary');

            // Hide custom month selector by default
            if (customMonthSelector) {
                customMonthSelector.classList.add('d-none');
            }

            // Calculate dates based on preset
            var today = new Date();
            var startDate, endDate;

            switch(preset) {
                case 'today':
                    startDate = today;
                    endDate = today;
                    break;

                case 'yesterday':
                    startDate = new Date(today);
                    startDate.setDate(today.getDate() - 1);
                    endDate = startDate;
                    break;

                case 'this_week':
                    // Get first day of current week (Sunday)
                    startDate = new Date(today);
                    startDate.setDate(today.getDate() - today.getDay());
                    endDate = today;
                    break;

                case 'last_week':
                    // Get first day of last week
                    startDate = new Date(today);
                    startDate.setDate(today.getDate() - today.getDay() - 7);
                    // Get last day of last week
                    endDate = new Date(startDate);
                    endDate.setDate(startDate.getDate() + 6);
                    break;

                case 'this_month':
                    // Try to use company-defined month periods first
                    if (window.monthDatesConfig) {
                        // Get current month number (1-12)
                        var currentMonth = today.getMonth() + 1;
                        if (currentMonth in window.monthDatesConfig) {
                            // Use company-defined period
                            var monthConfig = window.monthDatesConfig[currentMonth];
                            if (monthConfig.start && monthConfig.end) {
                                startDate = new Date(monthConfig.start);
                                // If end date is in the future, use today instead
                                var configEndDate = new Date(monthConfig.end);
                                endDate = configEndDate > today ? today : configEndDate;
                                break;
                            }
                        }
                    }
                    // Fallback to standard calendar month if no config found
                    startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                    endDate = today;
                    break;

                case 'last_month':
                    // Try to use company-defined month periods first
                    if (window.monthDatesConfig) {
                        // Get last month number (1-12)
                        var lastMonth = today.getMonth(); // 0-based, so this is already last month
                        if (lastMonth === 0) lastMonth = 12; // December of previous year

                        if (lastMonth in window.monthDatesConfig) {
                            // Use company-defined period
                            var monthConfig = window.monthDatesConfig[lastMonth];
                            if (monthConfig.start && monthConfig.end) {
                                startDate = new Date(monthConfig.start);
                                endDate = new Date(monthConfig.end);
                                break;
                            }
                        }
                    }
                    // Fallback to standard calendar month if no config found
                    startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                    endDate = new Date(today.getFullYear(), today.getMonth(), 0);
                    break;

                case 'custom_month':
                    // Show custom month selector
                    if (customMonthSelector) {
                        customMonthSelector.classList.remove('d-none');
                    }
                    return; // Don't set dates yet
            }

            // Format dates as YYYY-MM-DD for input fields
            if (startDateInput && endDateInput) {
                startDateInput.value = formatDateForInput(startDate);
                endDateInput.value = formatDateForInput(endDate);
            }
        });
    });

    // Custom month selector
    var applyCustomMonthBtn = document.getElementById('apply-custom-month');
    if (applyCustomMonthBtn) {
        applyCustomMonthBtn.addEventListener('click', function() {
            var monthSelect = document.getElementById('custom_month');
            var yearSelect = document.getElementById('custom_year');

            if (!monthSelect || !yearSelect) return;

            var month = parseInt(monthSelect.value);
            var year = parseInt(yearSelect.value);
            var startDateInput = document.getElementById('start_date');
            var endDateInput = document.getElementById('end_date');

            // Try to use company-defined month periods first
            if (window.monthDatesConfig && month in window.monthDatesConfig) {
                var monthConfig = window.monthDatesConfig[month];
                if (monthConfig.start && monthConfig.end) {
                    // Parse dates from config
                    var configStartDate = new Date(monthConfig.start);
                    var configEndDate = new Date(monthConfig.end);

                    // Adjust year if needed (config might be for a different year)
                    var startYear = configStartDate.getFullYear();
                    var endYear = configEndDate.getFullYear();
                    var yearDiff = year - startYear;

                    if (yearDiff !== 0) {
                        // Adjust dates to the selected year
                        configStartDate.setFullYear(year);
                        configEndDate.setFullYear(year);
                    }

                    // Use the company-defined period
                    if (startDateInput && endDateInput) {
                        startDateInput.value = formatDateForInput(configStartDate);
                        endDateInput.value = formatDateForInput(configEndDate);
                    }

                    console.log('Using company-defined period for month ' + month + ': ' +
                                formatDateForInput(configStartDate) + ' to ' +
                                formatDateForInput(configEndDate));
                } else {
                    console.log('Company-defined period for month ' + month + ' is incomplete, using standard calendar');
                    useStandardCalendarMonth(month, year, startDateInput, endDateInput);
                }
            } else {
                console.log('No company-defined period for month ' + month + ', using standard calendar');
                useStandardCalendarMonth(month, year, startDateInput, endDateInput);
            }

            // Hide custom month selector
            var customMonthSelector = document.getElementById('custom-month-selector');
            if (customMonthSelector) {
                customMonthSelector.classList.add('d-none');
            }
        });
    }

    // Helper function to use standard calendar month
    function useStandardCalendarMonth(month, year, startDateInput, endDateInput) {
        // First day of selected month
        var startDate = new Date(year, month - 1, 1);

        // Last day of selected month
        var endDate = new Date(year, month, 0);

        // Format dates as YYYY-MM-DD for input fields
        if (startDateInput && endDateInput) {
            startDateInput.value = formatDateForInput(startDate);
            endDateInput.value = formatDateForInput(endDate);
        }
    }
});

// Helper function to format date as YYYY-MM-DD
function formatDateForInput(date) {
    var year = date.getFullYear();
    var month = (date.getMonth() + 1).toString().padStart(2, '0');
    var day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}
