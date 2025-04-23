import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
import matplotlib.pyplot as plt
from io import BytesIO
import base64

# Configure logging
logger = logging.getLogger(__name__)

# Define model save paths
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai_models')
ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, 'anomaly_detection_model.joblib')
ATTENDANCE_PREDICTION_MODEL_PATH = os.path.join(MODEL_DIR, 'attendance_prediction_model.joblib')

# Ensure model directory exists
os.makedirs(MODEL_DIR, exist_ok=True)

class BiometricAI:
    """AI functionality for biometric data analysis and predictions"""
    
    @staticmethod
    def preprocess_attendance_data(attendance_records):
        """
        Preprocess attendance records for AI analysis
        
        Args:
            attendance_records: List of AttendanceRecord objects
        
        Returns:
            Pandas DataFrame with preprocessed data
        """
        data = []
        
        for record in attendance_records:
            # Extract features
            row = {
                'employee_id': record.employee_id,
                'date': record.date,
                'weekday': record.weekday,
                'attendance_status': record.attendance_status
            }
            
            # Calculate work duration if available
            if record.clock_in and record.clock_out:
                duration = (record.clock_out - record.clock_in).total_seconds() / 3600  # hours
                row['work_duration'] = duration
            else:
                row['work_duration'] = None
                
            # Add to dataset
            data.append(row)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Add weekday as numeric feature
        weekday_map = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 
            'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        df['weekday_num'] = df['weekday'].map(weekday_map)
        
        # Add month feature
        df['month'] = df['date'].apply(lambda x: x.month)
        
        # Convert attendance status to binary (present=1, absent=0)
        df['is_present'] = df['attendance_status'].apply(lambda x: 1 if x == 'P' else 0)
        
        return df
    
    @staticmethod
    def detect_attendance_anomalies(attendance_records):
        """
        Detect anomalies in attendance patterns
        
        Args:
            attendance_records: List of AttendanceRecord objects
        
        Returns:
            List of dictionaries containing anomalies with employee_id, date, and anomaly_type
        """
        try:
            # Preprocess data
            df = BiometricAI.preprocess_attendance_data(attendance_records)
            
            # Check if we have enough data
            if len(df) < 10:
                logger.warning("Not enough data for anomaly detection")
                return []
            
            # Filter only records with work duration
            df_duration = df.dropna(subset=['work_duration']).copy()
            
            if len(df_duration) < 10:
                logger.warning("Not enough records with work duration for anomaly detection")
                return []
            
            # Features for anomaly detection
            features = df_duration[['employee_id', 'weekday_num', 'work_duration']].copy()
            
            # Group by employee and weekday to get average work duration
            avg_duration = features.groupby(['employee_id', 'weekday_num'])['work_duration'].mean().reset_index()
            
            # Get employee-specific averages for comparison
            employee_avg = features.groupby('employee_id')['work_duration'].mean().to_dict()
            
            # Standardize features for anomaly detection
            scaler = StandardScaler()
            X = scaler.fit_transform(avg_duration[['weekday_num', 'work_duration']])
            
            # Create or load isolation forest model
            if os.path.exists(ANOMALY_MODEL_PATH):
                model = joblib.load(ANOMALY_MODEL_PATH)
            else:
                model = IsolationForest(contamination=0.05, random_state=42)
                model.fit(X)
                joblib.dump(model, ANOMALY_MODEL_PATH)
            
            # Predict anomalies
            avg_duration['anomaly'] = model.predict(X)
            anomaly_records = avg_duration[avg_duration['anomaly'] == -1]
            
            # Find specific records that match the anomaly patterns
            anomalies = []
            for _, row in anomaly_records.iterrows():
                emp_id = row['employee_id']
                weekday = row['weekday_num']
                
                # Find all records for this employee on this weekday
                emp_records = df_duration[
                    (df_duration['employee_id'] == emp_id) & 
                    (df_duration['weekday_num'] == weekday)
                ]
                
                for _, record in emp_records.iterrows():
                    # Compare with employee's average
                    emp_avg = employee_avg.get(emp_id, 0)
                    deviation = abs(record['work_duration'] - emp_avg) / (emp_avg if emp_avg > 0 else 1)
                    
                    if deviation > 0.25:  # More than 25% deviation from average
                        anomalies.append({
                            'employee_id': emp_id,
                            'date': record['date'],
                            'anomaly_type': 'unusual_duration',
                            'actual_hours': round(record['work_duration'], 2),
                            'average_hours': round(emp_avg, 2),
                            'deviation': f"{round(deviation * 100, 1)}%"
                        })
            
            # Also detect pattern breaks (absent when usually present)
            attendance_patterns = df.groupby(['employee_id', 'weekday_num'])['is_present'].mean().reset_index()
            
            for _, row in attendance_patterns.iterrows():
                emp_id = row['employee_id']
                weekday = row['weekday_num']
                presence_rate = row['is_present']
                
                if presence_rate > 0.8:  # Employee is usually present on this day
                    # Find absences on days they're usually present
                    pattern_breaks = df[
                        (df['employee_id'] == emp_id) & 
                        (df['weekday_num'] == weekday) & 
                        (df['is_present'] == 0)  # Absent
                    ]
                    
                    for _, record in pattern_breaks.iterrows():
                        anomalies.append({
                            'employee_id': emp_id,
                            'date': record['date'],
                            'anomaly_type': 'unexpected_absence',
                            'usual_presence_rate': f"{round(presence_rate * 100, 1)}%"
                        })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting attendance anomalies: {str(e)}")
            return []
    
    @staticmethod
    def predict_attendance(employee_id, date_to_predict=None):
        """
        Predict whether an employee will be present or absent on a specific date
        
        Args:
            employee_id: ID of the employee to predict for
            date_to_predict: Date to predict attendance for (default: tomorrow)
        
        Returns:
            Dictionary with prediction results
        """
        try:
            from models import AttendanceRecord, Employee
            
            # Default to tomorrow if date not provided
            if date_to_predict is None:
                date_to_predict = datetime.now().date() + timedelta(days=1)
            
            # Get historical attendance for this employee
            attendance_records = AttendanceRecord.query.filter_by(employee_id=employee_id).all()
            
            if len(attendance_records) < 10:
                return {
                    'employee_id': employee_id,
                    'date': date_to_predict,
                    'prediction': None,
                    'confidence': 0,
                    'message': 'Not enough historical data'
                }
            
            # Preprocess data
            df = BiometricAI.preprocess_attendance_data(attendance_records)
            
            # Prepare features
            X = df[['weekday_num', 'month']].copy()
            y = df['is_present'].values
            
            # Create or load prediction model
            if os.path.exists(ATTENDANCE_PREDICTION_MODEL_PATH):
                model = joblib.load(ATTENDANCE_PREDICTION_MODEL_PATH)
            else:
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X, y)
                joblib.dump(model, ATTENDANCE_PREDICTION_MODEL_PATH)
            
            # Prepare prediction input
            prediction_date = date_to_predict
            input_features = np.array([[
                prediction_date.weekday(),
                prediction_date.month
            ]])
            
            # Make prediction
            prediction = model.predict(input_features)[0]
            prediction_proba = model.predict_proba(input_features)[0]
            confidence = prediction_proba[1] if prediction == 1 else prediction_proba[0]
            
            return {
                'employee_id': employee_id,
                'date': prediction_date,
                'prediction': 'Present' if prediction == 1 else 'Absent',
                'confidence': round(confidence * 100, 1),
                'status': prediction
            }
            
        except Exception as e:
            logger.error(f"Error predicting attendance: {str(e)}")
            return {
                'employee_id': employee_id,
                'date': date_to_predict if date_to_predict else datetime.now().date() + timedelta(days=1),
                'prediction': None,
                'confidence': 0,
                'message': f'Error: {str(e)}'
            }
    
    @staticmethod
    def predict_department_attendance(department_id, date_to_predict=None):
        """
        Predict attendance for an entire department
        
        Args:
            department_id: ID of the department
            date_to_predict: Date to predict attendance for (default: tomorrow)
        
        Returns:
            Dictionary with department prediction statistics
        """
        try:
            from models import Employee
            
            # Default to tomorrow if date not provided
            if date_to_predict is None:
                date_to_predict = datetime.now().date() + timedelta(days=1)
            
            # Get all employees in department
            employees = Employee.query.filter_by(department_id=department_id, active=True).all()
            
            if not employees:
                return {
                    'department_id': department_id,
                    'date': date_to_predict,
                    'message': 'No active employees in department'
                }
            
            # Get predictions for each employee
            predictions = []
            for employee in employees:
                prediction = BiometricAI.predict_attendance(employee.id, date_to_predict)
                predictions.append(prediction)
            
            # Calculate department statistics
            total_employees = len(predictions)
            predicted_present = sum(1 for p in predictions if p.get('prediction') == 'Present')
            predicted_absent = total_employees - predicted_present
            
            # Calculate attendance rate
            attendance_rate = (predicted_present / total_employees) * 100 if total_employees > 0 else 0
            
            return {
                'department_id': department_id,
                'date': date_to_predict,
                'total_employees': total_employees,
                'predicted_present': predicted_present,
                'predicted_absent': predicted_absent,
                'attendance_rate': round(attendance_rate, 1),
                'employee_predictions': predictions
            }
            
        except Exception as e:
            logger.error(f"Error predicting department attendance: {str(e)}")
            return {
                'department_id': department_id,
                'date': date_to_predict if date_to_predict else datetime.now().date() + timedelta(days=1),
                'message': f'Error: {str(e)}'
            }
    
    @staticmethod
    def identify_attendance_patterns(employee_id=None, department_id=None):
        """
        Identify attendance patterns for employees or departments
        
        Args:
            employee_id: Optional employee ID to analyze
            department_id: Optional department ID to analyze
            
        Returns:
            Dictionary with pattern analysis results
        """
        try:
            from models import AttendanceRecord, Employee
            
            # Query records based on input parameters
            query = AttendanceRecord.query
            
            if employee_id:
                query = query.filter_by(employee_id=employee_id)
            elif department_id:
                # Get all employees in department
                employee_ids = [e.id for e in Employee.query.filter_by(department_id=department_id).all()]
                query = query.filter(AttendanceRecord.employee_id.in_(employee_ids))
            
            # Get attendance records
            attendance_records = query.all()
            
            if len(attendance_records) < 20:
                return {
                    'message': 'Not enough data for pattern analysis',
                    'patterns': []
                }
            
            # Preprocess data
            df = BiometricAI.preprocess_attendance_data(attendance_records)
            
            # Analyze attendance by weekday
            weekday_attendance = df.groupby('weekday_num')['is_present'].mean().reset_index()
            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_attendance['weekday'] = weekday_attendance['weekday_num'].apply(lambda x: weekday_names[int(x)])
            
            # Analyze work duration patterns for present employees
            present_records = df[df['is_present'] == 1].copy()
            duration_patterns = {}
            
            if not present_records.empty and 'work_duration' in present_records.columns:
                duration_patterns = present_records.groupby('weekday_num')['work_duration'].agg(['mean', 'std']).reset_index()
                duration_patterns['weekday'] = duration_patterns['weekday_num'].apply(lambda x: weekday_names[int(x)])
            
            # Identify common absence patterns
            absence_patterns = []
            
            # Check for consecutive absences
            if employee_id:
                employee_records = df[df['employee_id'] == employee_id].sort_values('date')
                
                consecutive_absences = []
                current_streak = []
                
                for i, row in employee_records.iterrows():
                    if row['is_present'] == 0:  # Absent
                        current_streak.append(row['date'])
                    else:
                        # If streak is broken and was at least 2 days
                        if len(current_streak) >= 2:
                            consecutive_absences.append({
                                'start_date': min(current_streak),
                                'end_date': max(current_streak),
                                'days': len(current_streak)
                            })
                        current_streak = []
                
                if len(current_streak) >= 2:
                    consecutive_absences.append({
                        'start_date': min(current_streak),
                        'end_date': max(current_streak),
                        'days': len(current_streak)
                    })
                
                absence_patterns = consecutive_absences
            
            # Format results
            weekday_pattern = [
                {
                    'weekday': row['weekday'],
                    'attendance_rate': round(row['is_present'] * 100, 1)
                }
                for _, row in weekday_attendance.iterrows()
            ]
            
            duration_pattern = []
            if not duration_patterns == {}:
                duration_pattern = [
                    {
                        'weekday': row['weekday'],
                        'avg_hours': round(row['mean'], 1),
                        'std_deviation': round(row['std'], 1)
                    }
                    for _, row in duration_patterns.iterrows()
                ]
            
            return {
                'weekday_patterns': weekday_pattern,
                'work_duration_patterns': duration_pattern,
                'absence_patterns': absence_patterns
            }
            
        except Exception as e:
            logger.error(f"Error identifying attendance patterns: {str(e)}")
            return {
                'message': f'Error: {str(e)}',
                'patterns': []
            }
    
    @staticmethod
    def generate_attendance_forecast(department_id, days=7):
        """
        Generate attendance forecast for a department for the next specified number of days
        
        Args:
            department_id: Department ID to forecast for
            days: Number of days to forecast
            
        Returns:
            Dictionary with forecast data
        """
        try:
            # Get all active employees in department
            from models import Employee
            employees = Employee.query.filter_by(department_id=department_id, active=True).all()
            
            if not employees:
                return {
                    'department_id': department_id,
                    'message': 'No active employees in department',
                    'forecast': []
                }
            
            # Generate predictions for each day
            forecast = []
            start_date = datetime.now().date() + timedelta(days=1)
            
            for i in range(days):
                forecast_date = start_date + timedelta(days=i)
                day_forecast = BiometricAI.predict_department_attendance(department_id, forecast_date)
                
                # Simplify the forecast data
                forecast.append({
                    'date': forecast_date,
                    'weekday': forecast_date.strftime('%A'),
                    'predicted_attendance_rate': day_forecast.get('attendance_rate', 0),
                    'predicted_present': day_forecast.get('predicted_present', 0),
                    'predicted_absent': day_forecast.get('predicted_absent', 0)
                })
            
            return {
                'department_id': department_id,
                'total_employees': len(employees),
                'forecast': forecast
            }
            
        except Exception as e:
            logger.error(f"Error generating attendance forecast: {str(e)}")
            return {
                'department_id': department_id,
                'message': f'Error: {str(e)}',
                'forecast': []
            }
    
    @staticmethod
    def generate_attendance_chart(department_id=None, employee_id=None, days=30):
        """
        Generate an attendance chart image for a department or employee
        
        Args:
            department_id: Optional department ID for chart
            employee_id: Optional employee ID for chart
            days: Number of past days to include
            
        Returns:
            Base64 encoded image
        """
        try:
            from models import AttendanceRecord, Employee
            
            # Set up query
            query = AttendanceRecord.query
            title = "Attendance"
            
            # Filter by department or employee
            if employee_id:
                query = query.filter_by(employee_id=employee_id)
                employee = Employee.query.get(employee_id)
                title = f"Attendance for {employee.name}" if employee else "Employee Attendance"
            elif department_id:
                # Get all employees in department
                employee_ids = [e.id for e in Employee.query.filter_by(department_id=department_id).all()]
                query = query.filter(AttendanceRecord.employee_id.in_(employee_ids))
                title = f"Department Attendance"
            
            # Filter by date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            query = query.filter(AttendanceRecord.date >= start_date, AttendanceRecord.date <= end_date)
            
            # Get records
            attendance_records = query.all()
            
            if not attendance_records:
                # Create a simple "No data" image
                plt.figure(figsize=(10, 6))
                plt.text(0.5, 0.5, "No attendance data available", 
                         ha='center', va='center', fontsize=16)
                plt.gca().set_axis_off()
                
                # Save to bytes
                buffer = BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                image_data = base64.b64encode(buffer.read()).decode('utf-8')
                plt.close()
                
                return image_data
            
            # Process data
            df = BiometricAI.preprocess_attendance_data(attendance_records)
            
            # Group by date and calculate attendance rate
            daily_attendance = df.groupby('date')['is_present'].mean().reset_index()
            
            # Create plot
            plt.figure(figsize=(12, 6))
            plt.plot(daily_attendance['date'], daily_attendance['is_present'] * 100, 'b-', marker='o')
            plt.title(f"{title} ({start_date} to {end_date})")
            plt.xlabel('Date')
            plt.ylabel('Attendance Rate (%)')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Add trend line
            if len(daily_attendance) > 5:
                z = np.polyfit(range(len(daily_attendance)), daily_attendance['is_present'] * 100, 1)
                p = np.poly1d(z)
                plt.plot(daily_attendance['date'], p(range(len(daily_attendance))), "r--", alpha=0.8, 
                        label=f"Trend: {'↑' if z[0] > 0 else '↓'}")
                plt.legend()
            
            # Save to bytes
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_data = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()
            
            return image_data
            
        except Exception as e:
            logger.error(f"Error generating attendance chart: {str(e)}")
            
            # Create error image
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5, f"Error generating chart: {str(e)}", 
                    ha='center', va='center', fontsize=12)
            plt.gca().set_axis_off()
            
            # Save to bytes
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_data = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()
            
            return image_data
    
    @staticmethod
    def cluster_employees_by_attendance(department_id=None):
        """
        Cluster employees based on attendance patterns
        
        Args:
            department_id: Optional department ID to filter employees
            
        Returns:
            Dictionary with clustering results
        """
        try:
            from models import AttendanceRecord, Employee
            
            # Get employees to analyze
            query = Employee.query.filter_by(active=True)
            if department_id:
                query = query.filter_by(department_id=department_id)
                
            employees = query.all()
            
            if not employees:
                return {
                    'message': 'No active employees found',
                    'clusters': []
                }
            
            # Collect attendance stats for each employee
            employee_stats = []
            
            for emp in employees:
                # Get attendance records
                records = AttendanceRecord.query.filter_by(employee_id=emp.id).all()
                
                if not records:
                    continue
                    
                # Calculate metrics
                df = BiometricAI.preprocess_attendance_data(records)
                
                # Metrics to use for clustering
                attendance_rate = df['is_present'].mean()
                
                # Check if we have work duration data
                work_duration_avg = None
                if 'work_duration' in df.columns:
                    work_duration_data = df.dropna(subset=['work_duration'])
                    if not work_duration_data.empty:
                        work_duration_avg = work_duration_data['work_duration'].mean()
                
                # Calculate consistency (standard deviation of arrival times)
                consistency = 0
                if 'clock_in' in df.columns:
                    clock_in_times = df.dropna(subset=['clock_in'])
                    if not clock_in_times.empty:
                        # Extract hour and minute and convert to minutes since midnight
                        minutes = clock_in_times['clock_in'].apply(
                            lambda x: x.hour * 60 + x.minute if hasattr(x, 'hour') else None
                        )
                        if not minutes.empty:
                            consistency = minutes.std() if not pd.isna(minutes.std()) else 0
                
                # Store employee stats
                employee_stats.append({
                    'employee_id': emp.id,
                    'name': emp.name,
                    'attendance_rate': attendance_rate,
                    'work_duration_avg': work_duration_avg if work_duration_avg is not None else 0,
                    'consistency': consistency
                })
            
            # Check if we have enough data
            if len(employee_stats) < 3:
                return {
                    'message': 'Not enough employees with attendance data for clustering',
                    'clusters': []
                }
            
            # Convert to DataFrame
            df_stats = pd.DataFrame(employee_stats)
            
            # Features for clustering
            features = ['attendance_rate', 'work_duration_avg', 'consistency']
            X = df_stats[features].values
            
            # Standardize features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Determine optimal number of clusters (between 2-4)
            n_clusters = min(4, len(employee_stats) // 2) if len(employee_stats) > 4 else 2
            
            # Apply KMeans clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            df_stats['cluster'] = kmeans.fit_predict(X_scaled)
            
            # Analyze clusters
            cluster_analysis = []
            for i in range(n_clusters):
                cluster_df = df_stats[df_stats['cluster'] == i]
                
                # Determine cluster characteristics
                avg_attendance = cluster_df['attendance_rate'].mean()
                avg_duration = cluster_df['work_duration_avg'].mean() if 'work_duration_avg' in cluster_df else 0
                
                # Determine cluster name based on characteristics
                if avg_attendance > 0.9:
                    cluster_type = "High Attendance"
                elif avg_attendance > 0.75:
                    cluster_type = "Regular Attendance"
                else:
                    cluster_type = "Low Attendance"
                    
                if avg_duration > 9:
                    cluster_type += ", Long Hours"
                elif avg_duration > 7:
                    cluster_type += ", Standard Hours"
                elif avg_duration > 0:
                    cluster_type += ", Short Hours"
                
                cluster_analysis.append({
                    'cluster_id': i,
                    'cluster_type': cluster_type,
                    'employee_count': len(cluster_df),
                    'avg_attendance_rate': round(avg_attendance * 100, 1),
                    'avg_work_hours': round(avg_duration, 1),
                    'employees': cluster_df[['employee_id', 'name']].to_dict('records')
                })
            
            return {
                'total_employees': len(employee_stats),
                'clusters': cluster_analysis
            }
            
        except Exception as e:
            logger.error(f"Error clustering employees: {str(e)}")
            return {
                'message': f'Error: {str(e)}',
                'clusters': []
            }
    
    @staticmethod
    def provide_optimization_recommendations(department_id=None):
        """
        Provide recommendations for workforce optimization based on attendance patterns
        
        Args:
            department_id: Optional department ID to filter
            
        Returns:
            List of recommendations
        """
        try:
            from models import Department, Employee, AttendanceRecord
            
            recommendations = []
            
            # Query departments
            if department_id:
                departments = [Department.query.get(department_id)]
            else:
                departments = Department.query.all()
            
            for dept in departments:
                if not dept:
                    continue
                    
                # Get employees in department
                employees = Employee.query.filter_by(department_id=dept.id, active=True).all()
                
                if not employees:
                    continue
                
                # Analyze department attendance
                employee_ids = [e.id for e in employees]
                
                # Get recent attendance (last 30 days)
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                
                records = AttendanceRecord.query.filter(
                    AttendanceRecord.employee_id.in_(employee_ids),
                    AttendanceRecord.date >= start_date,
                    AttendanceRecord.date <= end_date
                ).all()
                
                if not records:
                    continue
                
                # Process attendance data
                df = BiometricAI.preprocess_attendance_data(records)
                
                # Check department attendance rate
                attendance_rate = df['is_present'].mean()
                
                # Analyze by weekday
                weekday_attendance = df.groupby('weekday_num')['is_present'].mean()
                
                # Find lowest attendance weekday
                if not weekday_attendance.empty:
                    lowest_day_idx = weekday_attendance.idxmin()
                    lowest_day_rate = weekday_attendance.min()
                    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    lowest_day = weekday_names[lowest_day_idx]
                    
                    if lowest_day_rate < 0.75:
                        recommendations.append({
                            'department_id': dept.id,
                            'department_name': dept.name,
                            'type': 'attendance_improvement',
                            'priority': 'high' if lowest_day_rate < 0.6 else 'medium',
                            'description': f"Low attendance rate ({round(lowest_day_rate * 100, 1)}%) detected on {lowest_day}s",
                            'recommendation': f"Investigate reasons for low attendance on {lowest_day}s and implement incentives to improve attendance."
                        })
                
                # Check for overworking patterns
                if 'work_duration' in df.columns:
                    work_df = df.dropna(subset=['work_duration'])
                    if not work_df.empty:
                        avg_hours = work_df['work_duration'].mean()
                        max_hours = work_df['work_duration'].max()
                        
                        if avg_hours > 9.5:
                            recommendations.append({
                                'department_id': dept.id,
                                'department_name': dept.name,
                                'type': 'workload_management',
                                'priority': 'medium',
                                'description': f"High average working hours ({round(avg_hours, 1)} hours/day) detected",
                                'recommendation': "Consider workload distribution or additional staffing to prevent burnout."
                            })
                        
                        if max_hours > 12:
                            recommendations.append({
                                'department_id': dept.id,
                                'department_name': dept.name,
                                'type': 'policy_enforcement',
                                'priority': 'high',
                                'description': f"Extremely long shifts detected (maximum: {round(max_hours, 1)} hours)",
                                'recommendation': "Enforce work hour policies and investigate reasons for extended shifts."
                            })
                
                # Check consistency of attendance
                if len(employees) >= 5:
                    # Get attendance consistency score
                    employee_attendance = {}
                    
                    for emp in employees:
                        emp_records = df[df['employee_id'] == emp.id]
                        if not emp_records.empty:
                            employee_attendance[emp.id] = emp_records['is_present'].mean()
                    
                    if employee_attendance:
                        attendance_values = list(employee_attendance.values())
                        attendance_std = np.std(attendance_values)
                        
                        if attendance_std > 0.25:  # High variation in attendance among employees
                            recommendations.append({
                                'department_id': dept.id,
                                'department_name': dept.name,
                                'type': 'attendance_consistency',
                                'priority': 'medium',
                                'description': f"High variation in attendance rates among employees",
                                'recommendation': "Implement standardized attendance policies and identify outliers for targeted intervention."
                            })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return [{
                'type': 'error',
                'description': f"Error generating recommendations: {str(e)}",
                'recommendation': "Please try again later or contact support."
            }]