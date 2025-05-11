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
        if (!timeString) return '';

        // If it's already in HH:MM format, return as is
        if (typeof timeString === 'string' && timeString.match(/^\d{1,2}:\d{2}$/)) {
            return timeString;
        }

        // Otherwise, try to parse as date
        const options = { hour: '2-digit', minute: '2-digit' };
        try {
            return new Date(timeString).toLocaleTimeString(undefined, options);
        } catch (e) {
            return timeString; // Return original if parsing fails
        }
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

    // Load dashboard data if on dashboard page
    const dashboardPage = document.getElementById('dashboard-page');
    if (dashboardPage) {
        console.log('Dashboard page detected, loading data...');
        // Ensure the function exists before calling it
        if (typeof loadDashboardData === 'function') {
            loadDashboardData();
        } else if (typeof window.loadDashboardData === 'function') {
            window.loadDashboardData();
        } else {
            console.error('loadDashboardData function not found');
        }

        // Refresh dashboard button
        const refreshBtn = document.getElementById('refresh-dashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                this.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Refreshing...';
                if (typeof loadDashboardData === 'function') {
                    loadDashboardData().then(() => {
                        setTimeout(() => {
                            this.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
                        }, 500);
                    });
                } else if (typeof window.loadDashboardData === 'function') {
                    window.loadDashboardData().then(() => {
                        setTimeout(() => {
                            this.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
                        }, 500);
                    });
                }
            });
        }
    }

    // Sync status indicator
    updateSyncStatusFromServer();  // Cambiado a nueva función que consulta el servidor

    // Update sync status periodically
    setInterval(updateSyncStatusFromServer, 5000); // Consulta cada 5 segundos en lugar de 60 segundos

    // Nueva función que consulta el estado desde el servidor
    function updateSyncStatusFromServer() {
        const syncStatusElement = document.getElementById('sync-status');
        if (!syncStatusElement) return;

        // Consultar el estado real desde el servidor
        fetch('/check_sync_status')
            .then(response => response.json())
            .then(data => {
                console.log('Estado actual de la sincronización:', data);

                // Actualizar el estado en la interfaz
                const status = data.status || 'none';
                const message = data.message || '';

                // Elemento principal de estado
                let statusHTML = '';

                switch(status) {
                    case 'success':
                        statusHTML = `<span class="badge bg-success me-2"><i class="fas fa-check"></i></span><span>${message}</span>`;
                        // Si hay pasos visibles, actualizarlos también
                        setAllStepsComplete();
                        break;
                    case 'error':
                        statusHTML = `<span class="badge bg-danger me-2"><i class="fas fa-times"></i></span><span>${message}</span>`;
                        break;
                    case 'in_progress':
                        statusHTML = `<span class="badge bg-primary me-2"><i class="fas fa-sync-alt fa-spin"></i></span><span>${message}</span>`;

                        // Actualizar la barra de progreso y los pasos
                        updateSyncProgress(data);
                        break;
                    case 'cancelled':
                        statusHTML = `<span class="badge bg-warning me-2"><i class="fas fa-ban"></i></span><span>تم إلغاء المزامنة</span>`;
                        break;
                    default:
                        statusHTML = `<span class="badge bg-secondary me-2"><i class="fas fa-question"></i></span><span>لا توجد معلومات حول آخر مزامنة</span>`;
                }

                // Actualizar el estado en la interfaz
                syncStatusElement.innerHTML = statusHTML;

                // Mostrar/ocultar el botón de cancelación según el estado
                updateCancelButton(status === 'in_progress');
            })
            .catch(error => {
                console.error('Error al consultar el estado de la sincronización:', error);
            });
    }

    // Actualizar barra de progreso y pasos
    function updateSyncProgress(data) {
        // Mostrar los pasos si están ocultos
        const syncStepsEl = document.getElementById('sync-steps');
        if (syncStepsEl) {
            syncStepsEl.classList.remove('d-none');
        }

        // Actualizar barra de progreso
        const progressBar = document.getElementById('sync-progress-bar');
        if (progressBar) {
            const percent = data.progress || 0;
            progressBar.style.width = `${percent}%`;
            progressBar.setAttribute('aria-valuenow', percent);
            progressBar.textContent = data.progress_message || '';
        } else {
            // Crear barra de progreso si no existe
            const progressHTML = `
                <div class="progress mt-2" style="height: 25px;">
                    <div id="sync-progress-bar" class="progress-bar bg-primary progress-bar-striped progress-bar-animated"
                        role="progressbar" style="width: ${data.progress || 0}%;" aria-valuenow="${data.progress || 0}" aria-valuemin="0" aria-valuemax="100">
                        ${data.progress_message || ''}
                    </div>
                </div>
            `;

            const statusContainer = document.getElementById('sync-status-container');
            if (statusContainer) {
                // Insertar después del primer elemento (que es el estado)
                const firstChild = statusContainer.querySelector('.d-flex');
                if (firstChild) {
                    firstChild.insertAdjacentHTML('afterend', progressHTML);
                }
            }
        }

        // Actualizar pasos según el paso actual
        if (data.step) {
            const steps = ['connect', 'download', 'process', 'save', 'complete'];
            const currentStepIndex = steps.indexOf(data.step);

            for (let i = 0; i < steps.length; i++) {
                if (i < currentStepIndex) {
                    setStepStatus(steps[i], 'success');
                } else if (i === currentStepIndex) {
                    setStepStatus(steps[i], 'active');
                } else {
                    setStepStatus(steps[i], 'waiting');
                }
            }
        }
    }

    // Marcar todos los pasos como completados
    function setAllStepsComplete() {
        const steps = ['connect', 'download', 'process', 'save', 'complete'];
        steps.forEach(step => setStepStatus(step, 'success'));

        // Actualizar barra de progreso
        const progressBar = document.getElementById('sync-progress-bar');
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.setAttribute('aria-valuenow', 100);
            progressBar.textContent = 'اكتملت المزامنة بنجاح';
            progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
        }
    }

    // Mostrar/ocultar botón de cancelación
    function updateCancelButton(showButton) {
        const cancelBtn = document.getElementById('cancel-sync-btn');
        if (!cancelBtn) return;

        const cancelForm = cancelBtn.closest('form');
        if (cancelForm) {
            cancelForm.style.display = showButton ? 'block' : 'none';
        }
    }

    // Función para establecer el estado de un paso
    window.setStepStatus = function(step, status) {
        const stepEl = document.getElementById(`step-${step}`);
        const iconEl = document.getElementById(`${step}-icon`);
        if (!stepEl || !iconEl) return;

        // Remove existing status classes
        iconEl.classList.remove('bg-secondary', 'bg-primary', 'bg-success', 'bg-warning', 'bg-danger');

        // Add new status class and icon
        switch(status) {
            case 'active':
                iconEl.classList.add('bg-primary');
                iconEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                break;
            case 'success':
                iconEl.classList.add('bg-success');
                iconEl.innerHTML = '<i class="fas fa-check"></i>';
                break;
            case 'warning':
                iconEl.classList.add('bg-warning');
                iconEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                break;
            case 'error':
                iconEl.classList.add('bg-danger');
                iconEl.innerHTML = '<i class="fas fa-times"></i>';
                break;
            case 'pending':
                iconEl.classList.add('bg-primary');
                iconEl.innerHTML = '<i class="fas fa-clock"></i>';
                break;
            case 'waiting':
            default:
                iconEl.classList.add('bg-secondary');
                iconEl.innerHTML = '<i class="fas fa-circle"></i>';
                break;
        }
    };

    // Handle form submissions to prevent page reload during demo
    const demoForms = document.querySelectorAll('form.demo-form');
    demoForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            alert('Form submission would be processed on the server');
        });
    });

    // Function to load dashboard data from API
    window.loadDashboardData = function() {
        console.log('Fetching dashboard data from API...');
        return fetch('/api/dashboard/summary')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Dashboard data received:', data);

                // Update summary cards
                const totalEmployeesEl = document.getElementById('total-employees');
                const presentTodayEl = document.getElementById('present-today');
                const absentTodayEl = document.getElementById('absent-today');
                const onVacationEl = document.getElementById('on-vacation');

                if (totalEmployeesEl) totalEmployeesEl.textContent = data.total_employees || '--';
                if (presentTodayEl) presentTodayEl.textContent = data.present_today || '--';
                if (absentTodayEl) absentTodayEl.textContent = data.absent_today || '--';
                if (onVacationEl) onVacationEl.textContent = data.on_vacation || '--';

                // Update department summary
                const deptSummary = document.getElementById('dept-summary');
                if (deptSummary && data.departments && data.departments.length > 0) {
                    deptSummary.innerHTML = '';
                    data.departments.forEach(dept => {
                        deptSummary.innerHTML += `
                            <tr>
                                <td>${dept.name}</td>
                                <td>${dept.employee_count}</td>
                                <td><span class="badge bg-success">${dept.present_count}</span></td>
                            </tr>
                        `;
                    });
                } else if (deptSummary) {
                    deptSummary.innerHTML = '<tr><td colspan="3" class="text-center">No department data available</td></tr>';
                }

                // Update recent activity
                const recentActivity = document.getElementById('recent-activity');
                if (recentActivity && data.recent_activity && data.recent_activity.length > 0) {
                    recentActivity.innerHTML = '';
                    data.recent_activity.forEach(activity => {
                        const statusClass = activity.status === 'normal' ? 'bg-success' : 'bg-warning';
                        const statusText = activity.status === 'normal' ? 'On Time' : 'Late';
                        const activityType = activity.type === 'in' ? 'Clock In' : 'Clock Out';

                        recentActivity.innerHTML += `
                            <tr>
                                <td>${activity.employee_name || 'Unknown'}</td>
                                <td>${activity.time || '--'}</td>
                                <td>${activityType}</td>
                                <td>${activity.terminal || '--'}</td>
                                <td><span class="badge ${statusClass}">${statusText}</span></td>
                            </tr>
                        `;
                    });
                } else if (recentActivity) {
                    recentActivity.innerHTML = '<tr><td colspan="5" class="text-center">No recent activity data available</td></tr>';
                }

                // Update attendance chart if it exists
                const chartCanvas = document.getElementById('attendance-chart');
                if (chartCanvas && data.trend && data.trend.dates) {
                    const ctx = chartCanvas.getContext('2d');

                    // Destroy existing chart if it exists
                    if (window.attendanceChart) {
                        window.attendanceChart.destroy();
                    }

                    // Create new chart
                    window.attendanceChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.trend.dates,
                            datasets: [
                                {
                                    label: 'Present',
                                    data: data.trend.present,
                                    borderColor: '#28a745',
                                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                                    tension: 0.3,
                                    fill: true
                                },
                                {
                                    label: 'Absent',
                                    data: data.trend.absent,
                                    borderColor: '#dc3545',
                                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                                    tension: 0.3,
                                    fill: true
                                },
                                {
                                    label: 'Vacation',
                                    data: data.trend.vacation,
                                    borderColor: '#ffc107',
                                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                                    tension: 0.3,
                                    fill: true
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'top',
                                },
                                tooltip: {
                                    mode: 'index',
                                    intersect: false
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        precision: 0
                                    }
                                }
                            }
                        }
                    });
                } else if (chartCanvas) {
                    console.warn('Chart canvas exists but no trend data available');
                    // Display a message in the chart area
                    const ctx = chartCanvas.getContext('2d');
                    ctx.font = '14px Arial';
                    ctx.fillStyle = '#aaa';
                    ctx.textAlign = 'center';
                    ctx.fillText('No attendance data available', chartCanvas.width / 2, chartCanvas.height / 2);
                }

                return data;
            })
            .catch(error => {
                console.error('Error loading dashboard data:', error);

                // Show error messages in the UI elements
                const elements = ['dept-summary', 'recent-activity'];
                elements.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.innerHTML = `<tr><td colspan="5" class="text-center text-danger">
                            Error loading data: ${error.message || 'Unknown error'}
                        </td></tr>`;
                    }
                });

                // Show error in chart
                const chartCanvas = document.getElementById('attendance-chart');
                if (chartCanvas) {
                    const ctx = chartCanvas.getContext('2d');
                    ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);
                    ctx.font = '14px Arial';
                    ctx.fillStyle = '#dc3545';
                    ctx.textAlign = 'center';
                    ctx.fillText(`Error loading chart data: ${error.message || 'Unknown error'}`,
                        chartCanvas.width / 2, chartCanvas.height / 2);
                }
            });
    };
});
