/**
 * Enhanced Analytics Module for BiometricSync
 * Provides advanced data visualization and analysis functions
 */

class AttendanceAnalytics {
    /**
     * Initialize the analytics module
     * @param {Object} options Configuration options
     */
    constructor(options = {}) {
        this.options = Object.assign({
            lang: 'ar',
            colorScheme: 'dark',
            animationDuration: 1000
        }, options);
        
        // Chart color schemes
        this.colorSchemes = {
            dark: {
                background: 'rgba(33, 37, 41, 0.8)',
                text: '#ffffff',
                gridLines: 'rgba(255, 255, 255, 0.1)',
                present: 'rgba(40, 167, 69, 0.8)',
                absent: 'rgba(220, 53, 69, 0.8)',
                vacation: 'rgba(255, 193, 7, 0.8)',
                borderPresent: 'rgba(40, 167, 69, 1)',
                borderAbsent: 'rgba(220, 53, 69, 1)',
                borderVacation: 'rgba(255, 193, 7, 1)'
            },
            light: {
                background: 'rgba(248, 249, 250, 0.8)',
                text: '#212529',
                gridLines: 'rgba(0, 0, 0, 0.1)',
                present: 'rgba(40, 167, 69, 0.7)',
                absent: 'rgba(220, 53, 69, 0.7)',
                vacation: 'rgba(255, 193, 7, 0.7)',
                borderPresent: 'rgba(40, 167, 69, 1)',
                borderAbsent: 'rgba(220, 53, 69, 1)',
                borderVacation: 'rgba(255, 193, 7, 1)'
            }
        };
        
        // Day translations for Arabic/English
        this.dayNames = {
            en: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
            ar: ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
        };
        
        this.monthNames = {
            en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
            ar: ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
        };
        
        this.statusLabels = {
            en: { 'P': 'Present', 'A': 'Absent', 'V': 'Vacation', 'S': 'Sick', 'T': 'Transfer', 'E': 'Eid' },
            ar: { 'P': 'حاضر', 'A': 'غائب', 'V': 'إجازة', 'S': 'مريض', 'T': 'نقل', 'E': 'عيد' }
        };
    }
    
    /**
     * Create an attendance heatmap
     * @param {string} elementId DOM element ID for the chart
     * @param {Array} data Attendance data
     */
    createAttendanceHeatmap(elementId, data) {
        const colors = this.colorSchemes[this.options.colorScheme];
        const element = document.getElementById(elementId);
        
        if (!element) {
            console.error(`Element with ID "${elementId}" not found`);
            return;
        }
        
        // Process data to create heatmap
        const dates = [...new Set(data.map(d => d.date))].sort();
        const employees = [...new Set(data.map(d => d.employee))];
        
        // Create heatmap grid
        let html = '<div class="attendance-heatmap">';
        html += '<table class="heatmap-table">';
        
        // Header row with dates
        html += '<thead><tr><th></th>';
        dates.forEach(date => {
            const dateObj = new Date(date);
            html += `<th class="heatmap-date">
                <div class="date-num">${dateObj.getDate()}</div>
                <div class="date-day">${this.dayNames[this.options.lang][dateObj.getDay()].substring(0, 3)}</div>
            </th>`;
        });
        html += '</tr></thead>';
        
        // Rows for each employee
        html += '<tbody>';
        employees.forEach(emp => {
            html += `<tr><td class="employee-name">${emp}</td>`;
            
            dates.forEach(date => {
                const record = data.find(d => d.date === date && d.employee === emp);
                const status = record ? record.status : '';
                const color = this.getStatusColor(status);
                const title = this.statusLabels[this.options.lang][status] || '';
                
                html += `<td class="heatmap-cell" style="background-color: ${color}" title="${emp} - ${date} - ${title}">
                    <span class="status-indicator">${status}</span>
                </td>`;
            });
            
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        
        element.innerHTML = html;
    }
    
    /**
     * Get color for attendance status
     * @param {string} status Attendance status code
     * @returns {string} CSS color
     */
    getStatusColor(status) {
        const colors = this.colorSchemes[this.options.colorScheme];
        
        switch(status) {
            case 'P': return colors.present;
            case 'A': return colors.absent;
            case 'V': return colors.vacation;
            case 'S': return 'rgba(23, 162, 184, 0.8)'; // cyan for sick
            case 'T': return 'rgba(108, 117, 125, 0.8)'; // gray for transfer
            case 'E': return 'rgba(111, 66, 193, 0.8)'; // purple for Eid
            default: return 'rgba(0, 0, 0, 0.2)'; // transparent for unknown
        }
    }
    
    /**
     * Create an attendance overview chart
     * @param {string} elementId DOM element ID for the chart
     * @param {Array} data Attendance data
     */
    createAttendanceOverview(elementId, data) {
        const colors = this.colorSchemes[this.options.colorScheme];
        const ctx = document.getElementById(elementId).getContext('2d');
        
        // Process data to get attendance by status
        const dateGroups = data.reduce((acc, curr) => {
            const date = curr.date;
            if (!acc[date]) acc[date] = { date, P: 0, A: 0, V: 0, S: 0, T: 0, E: 0 };
            if (curr.status) acc[date][curr.status]++;
            return acc;
        }, {});
        
        const chartData = Object.values(dateGroups).sort((a, b) => 
            new Date(a.date) - new Date(b.date));
        
        const labels = chartData.map(d => {
            const date = new Date(d.date);
            return `${date.getDate()} ${this.monthNames[this.options.lang][date.getMonth()].substring(0, 3)}`;
        });
        
        const present = chartData.map(d => d.P);
        const absent = chartData.map(d => d.A);
        const vacation = chartData.map(d => d.V);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: this.statusLabels[this.options.lang].P,
                        data: present,
                        backgroundColor: colors.present,
                        borderColor: colors.borderPresent,
                        borderWidth: 1
                    },
                    {
                        label: this.statusLabels[this.options.lang].A,
                        data: absent,
                        backgroundColor: colors.absent,
                        borderColor: colors.borderAbsent,
                        borderWidth: 1
                    },
                    {
                        label: this.statusLabels[this.options.lang].V,
                        data: vacation,
                        backgroundColor: colors.vacation,
                        borderColor: colors.borderVacation,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: colors.text
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: colors.gridLines
                        },
                        ticks: {
                            color: colors.text
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: colors.gridLines
                        },
                        ticks: {
                            color: colors.text,
                            precision: 0
                        }
                    }
                },
                animation: {
                    duration: this.options.animationDuration
                }
            }
        });
    }
    
    /**
     * Create a work hours analysis chart
     * @param {string} elementId DOM element ID for the chart
     * @param {Array} data Work hours data
     */
    createWorkHoursChart(elementId, data) {
        const colors = this.colorSchemes[this.options.colorScheme];
        const ctx = document.getElementById(elementId).getContext('2d');
        
        // Group by day of week
        const dayGroups = data.reduce((acc, curr) => {
            const date = new Date(curr.date);
            const day = date.getDay(); // 0 = Sunday, 6 = Saturday
            if (!acc[day]) {
                acc[day] = {
                    day,
                    hours: [],
                    count: 0
                };
            }
            
            if (curr.hours > 0) {
                acc[day].hours.push(curr.hours);
                acc[day].count++;
            }
            
            return acc;
        }, {});
        
        // Calculate average work hours per day
        const dayStats = [];
        for (let i = 0; i < 7; i++) {
            const group = dayGroups[i] || { day: i, hours: [], count: 0 };
            const average = group.hours.length > 0 
                ? group.hours.reduce((a, b) => a + b, 0) / group.hours.length 
                : 0;
                
            dayStats.push({
                day: i,
                average: parseFloat(average.toFixed(2)),
                count: group.count
            });
        }
        
        // Prepare chart data
        const labels = dayStats.map(d => this.dayNames[this.options.lang][d.day]);
        const averageHours = dayStats.map(d => d.average);
        const sampleSize = dayStats.map(d => d.count);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: this.options.lang === 'ar' ? 'متوسط ساعات العمل' : 'Average Work Hours',
                    data: averageHours,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: colors.text
                        }
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const index = context.dataIndex;
                                return (this.options.lang === 'ar' ? 'عدد العينات: ' : 'Sample Size: ') + sampleSize[index];
                            }.bind(this)
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: colors.gridLines
                        },
                        ticks: {
                            color: colors.text
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: colors.gridLines
                        },
                        ticks: {
                            color: colors.text,
                            callback: function(value) {
                                return value + (this.options.lang === 'ar' ? ' ساعة' : ' hrs');
                            }.bind(this)
                        }
                    }
                },
                animation: {
                    duration: this.options.animationDuration
                }
            }
        });
    }
    
    /**
     * Process attendance data to calculate key metrics
     * @param {Array} data Raw attendance data
     * @returns {Object} Processed metrics
     */
    calculateAttendanceMetrics(data) {
        // Calculate attendance rate
        const totalRecords = data.length;
        const presentRecords = data.filter(d => d.status === 'P').length;
        const attendanceRate = totalRecords > 0 ? (presentRecords / totalRecords * 100).toFixed(1) : 0;
        
        // Calculate average work hours
        const recordsWithHours = data.filter(d => d.status === 'P' && d.hours > 0);
        const totalHours = recordsWithHours.reduce((sum, record) => sum + record.hours, 0);
        const averageHours = recordsWithHours.length > 0 
            ? (totalHours / recordsWithHours.length).toFixed(1) 
            : 0;
        
        // Calculate consistency (standard deviation of arrival times)
        const arrivalMinutes = [];
        data.filter(d => d.status === 'P' && d.clockIn)
            .forEach(record => {
                const [hours, minutes] = record.clockIn.split(':').map(Number);
                arrivalMinutes.push(hours * 60 + minutes);
            });
            
        let stdDeviation = 0;
        if (arrivalMinutes.length > 0) {
            const mean = arrivalMinutes.reduce((sum, val) => sum + val, 0) / arrivalMinutes.length;
            const squaredDiffs = arrivalMinutes.map(val => Math.pow(val - mean, 2));
            const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / squaredDiffs.length;
            stdDeviation = Math.sqrt(variance);
        }
        
        const consistencyScore = Math.max(0, 100 - stdDeviation / 5).toFixed(1);
        
        // Identify patterns
        const consecutiveAbsences = this.findConsecutiveAbsences(data);
        const weekendAttendance = this.analyzeWeekendAttendance(data);
        
        return {
            totalDays: totalRecords,
            presentDays: presentRecords,
            absentDays: data.filter(d => d.status === 'A').length,
            vacationDays: data.filter(d => d.status === 'V').length,
            attendanceRate: attendanceRate,
            averageHours: averageHours,
            consistencyScore: consistencyScore,
            consecutiveAbsences: consecutiveAbsences,
            weekendAttendance: weekendAttendance
        };
    }
    
    /**
     * Find patterns of consecutive absences
     * @param {Array} data Attendance data
     * @returns {Array} Consecutive absence patterns
     */
    findConsecutiveAbsences(data) {
        // Sort data by date
        const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
        
        const patterns = [];
        let currentStreak = [];
        
        for (let i = 0; i < sortedData.length; i++) {
            if (sortedData[i].status === 'A') {
                currentStreak.push(sortedData[i]);
            } else {
                if (currentStreak.length >= 2) {
                    patterns.push({
                        start: currentStreak[0].date,
                        end: currentStreak[currentStreak.length - 1].date,
                        days: currentStreak.length
                    });
                }
                currentStreak = [];
            }
        }
        
        // Check for streak at end of data
        if (currentStreak.length >= 2) {
            patterns.push({
                start: currentStreak[0].date,
                end: currentStreak[currentStreak.length - 1].date,
                days: currentStreak.length
            });
        }
        
        return patterns;
    }
    
    /**
     * Analyze weekend attendance patterns
     * @param {Array} data Attendance data
     * @returns {Object} Weekend attendance analysis
     */
    analyzeWeekendAttendance(data) {
        const weekendDays = [5, 6]; // Friday and Saturday - adjust if needed
        
        const weekendRecords = data.filter(record => {
            const date = new Date(record.date);
            return weekendDays.includes(date.getDay());
        });
        
        const presentOnWeekend = weekendRecords.filter(r => r.status === 'P').length;
        const weekendRate = weekendRecords.length > 0 
            ? (presentOnWeekend / weekendRecords.length * 100).toFixed(1)
            : 0;
            
        return {
            totalWeekends: weekendRecords.length,
            presentOnWeekend: presentOnWeekend,
            weekendRate: weekendRate
        };
    }
    
    /**
     * Generate employee performance score based on attendance data
     * @param {Array} data Attendance data
     * @returns {Object} Performance metrics
     */
    generatePerformanceScore(data) {
        // Calculate basic metrics
        const metrics = this.calculateAttendanceMetrics(data);
        
        // Weight each component
        const attendanceWeight = 0.5;
        const consistencyWeight = 0.3;
        const hoursWeight = 0.2;
        
        // Calculate weighted score
        const attendanceScore = Math.min(100, parseFloat(metrics.attendanceRate));
        const consistencyScore = parseFloat(metrics.consistencyScore);
        
        // Normalize hours score (assuming 8 is standard, max score at 9+)
        const avgHours = parseFloat(metrics.averageHours);
        const hoursScore = Math.min(100, (avgHours / 9) * 100);
        
        // Calculate overall score
        const overallScore = (
            attendanceScore * attendanceWeight +
            consistencyScore * consistencyWeight +
            hoursScore * hoursWeight
        ).toFixed(1);
        
        // Determine performance category
        let category;
        if (overallScore >= 90) {
            category = this.options.lang === 'ar' ? 'ممتاز' : 'Excellent';
        } else if (overallScore >= 80) {
            category = this.options.lang === 'ar' ? 'جيد جداً' : 'Very Good';
        } else if (overallScore >= 70) {
            category = this.options.lang === 'ar' ? 'جيد' : 'Good';
        } else if (overallScore >= 60) {
            category = this.options.lang === 'ar' ? 'مقبول' : 'Satisfactory';
        } else {
            category = this.options.lang === 'ar' ? 'يحتاج تحسين' : 'Needs Improvement';
        }
        
        return {
            overallScore: overallScore,
            category: category,
            components: {
                attendance: {
                    score: attendanceScore.toFixed(1),
                    weight: attendanceWeight * 100
                },
                consistency: {
                    score: consistencyScore,
                    weight: consistencyWeight * 100
                },
                hours: {
                    score: hoursScore.toFixed(1),
                    weight: hoursWeight * 100
                }
            }
        };
    }
    
    /**
     * Visualize performance score as a gauge chart
     * @param {string} elementId DOM element ID for the chart
     * @param {Object} performance Performance data
     */
    createPerformanceGauge(elementId, performance) {
        const element = document.getElementById(elementId);
        
        if (!element) {
            console.error(`Element with ID "${elementId}" not found`);
            return;
        }
        
        // Get colors based on score
        let gaugeColor;
        if (performance.overallScore >= 90) gaugeColor = '#28a745'; // green
        else if (performance.overallScore >= 80) gaugeColor = '#20c997'; // teal
        else if (performance.overallScore >= 70) gaugeColor = '#17a2b8'; // cyan
        else if (performance.overallScore >= 60) gaugeColor = '#ffc107'; // yellow
        else gaugeColor = '#dc3545'; // red
        
        const gauge = new Chart(element, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [performance.overallScore, 100 - performance.overallScore],
                    backgroundColor: [gaugeColor, '#e9ecef'],
                    borderWidth: 0
                }]
            },
            options: {
                circumference: 180,
                rotation: 270,
                cutout: '80%',
                plugins: {
                    tooltip: {
                        enabled: false
                    },
                    legend: {
                        display: false
                    }
                }
            }
        });
        
        // Add center text to the gauge
        const ctx = element.getContext('2d');
        const centerX = element.width / 2;
        const centerY = element.height / 2;
        
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        ctx.font = '20px Arial';
        ctx.fillStyle = gaugeColor;
        ctx.fillText(performance.overallScore, centerX, centerY - 15);
        
        ctx.font = '14px Arial';
        ctx.fillStyle = '#6c757d';
        ctx.fillText(performance.category, centerX, centerY + 15);
    }
}

// Export for use in other modules
window.AttendanceAnalytics = AttendanceAnalytics;