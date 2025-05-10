#!/usr/bin/env python
"""
This script enhances the PDF export functionality for the monthly timesheet
by creating a new route and template with improved styling and layout.
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_translations():
    """Add necessary translations for the PDF export functionality"""
    try:
        translations_file = os.path.join(os.getcwd(), 'translations.py')
        
        with open(translations_file, 'r', encoding='utf-8') as f:
            translations_content = f.read()
            
        # Add English translations if not present
        en_translations_to_add = {
            'generated': 'Generated',
            'report_id': 'Report ID',
            'page': 'Page',
            'of': 'of',
            'prepared_by': 'Prepared By',
            'approved_by': 'Approved By',
            'department_manager': 'Department Manager',
            'housing_maintenance_system': 'Housing Maintenance System'
        }
        
        # Add Arabic translations if not present
        ar_translations_to_add = {
            'generated': 'تم إنشاؤه',
            'report_id': 'رقم التقرير',
            'page': 'صفحة',
            'of': 'من',
            'prepared_by': 'أعده',
            'approved_by': 'اعتمده',
            'department_manager': 'مدير القسم',
            'housing_maintenance_system': 'نظام صيانة الإسكان'
        }
        
        # Update English translations
        en_section_pos = translations_content.find("'en': {")
        if en_section_pos != -1:
            for key, value in en_translations_to_add.items():
                if f"'{key}':" not in translations_content:
                    # Find the position to insert (before the closing brace of the English dict)
                    insert_pos = translations_content.find("    },", en_section_pos)
                    if insert_pos != -1:
                        translations_content = translations_content[:insert_pos] + f"        '{key}': '{value}',\n" + translations_content[insert_pos:]
        
        # Update Arabic translations
        ar_section_pos = translations_content.find("'ar': {")
        if ar_section_pos != -1:
            for key, value in ar_translations_to_add.items():
                if f"'{key}':" not in translations_content[ar_section_pos:]:
                    # Find the position to insert (before the closing brace of the Arabic dict)
                    insert_pos = translations_content.find("    }", ar_section_pos)
                    if insert_pos != -1:
                        translations_content = translations_content[:insert_pos] + f"        '{key}': '{value}',\n" + translations_content[insert_pos:]
                        
        # Write updated translations back to file
        with open(translations_file, 'w', encoding='utf-8') as f:
            f.write(translations_content)
            
        logger.info("Added new translations for PDF export functionality")
        return True
    except Exception as e:
        logger.error(f"Error adding translations: {str(e)}")
        return False


def update_js_export_function():
    """Update the timesheet.js file to use the new export route"""
    try:
        js_file_path = os.path.abspath(os.path.join('static', 'js', 'timesheet.js'))
        
        if not os.path.exists(js_file_path):
            logger.error(f"JavaScript file not found: {js_file_path}")
            return False
            
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
            
        # Check if we need to modify the export button click handler
        if "document.getElementById('export-pdf')" in js_content:
            export_btn_code = """
    // Add click handler for PDF export button
    const exportPdfBtn = document.getElementById('export-pdf');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function() {
            // Get current filter parameters
            const urlParams = new URLSearchParams(window.location.search);
            
            // Build URL for export with same parameters
            let exportUrl = '/export_timesheet?';
            if (urlParams.has('year')) exportUrl += 'year=' + urlParams.get('year') + '&';
            if (urlParams.has('month')) exportUrl += 'month=' + urlParams.get('month') + '&';
            if (urlParams.has('department')) exportUrl += 'department=' + urlParams.get('department') + '&';
            if (urlParams.has('housing')) exportUrl += 'housing=' + urlParams.get('housing') + '&';
            if (urlParams.has('start_date')) exportUrl += 'start_date=' + urlParams.get('start_date') + '&';
            if (urlParams.has('end_date')) exportUrl += 'end_date=' + urlParams.get('end_date');
            
            // Open the export URL in a new window
            window.open(exportUrl, '_blank');
        });
    }"""
            
            # Find a good place to insert this code
            insert_position = js_content.find("document.addEventListener('DOMContentLoaded'")
            if insert_position != -1:
                # Find the next closing brace of the DOMContentLoaded handler
                closing_brace_pos = js_content.find("});", insert_position)
                if closing_brace_pos != -1:
                    # Insert before the closing brace
                    js_content = js_content[:closing_brace_pos] + export_btn_code + js_content[closing_brace_pos:]
                    
                    with open(js_file_path, 'w', encoding='utf-8') as f:
                        f.write(js_content)
                        
                    logger.info("Updated timesheet.js with export button handler")
                    return True
            
            logger.warning("Could not find proper insertion point in timesheet.js")
            return False
        else:
            logger.info("Export button handler already exists in timesheet.js")
            return True
            
    except Exception as e:
        logger.error(f"Error updating JavaScript file: {str(e)}")
        return False


def enhance_timesheet_export():
    """Add a new route for exporting the timesheet to PDF with professional styling"""
    try:
        # Find the app.py file to add the new route
        app_file_path = os.path.join(os.getcwd(), 'app.py')
        
        with open(app_file_path, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        # Add translations
        add_translations()
        
        # Define the new route that needs to be added
        new_route = """
@app.route('/export_timesheet', methods=['GET'])
def export_timesheet():
    \"\"\"Export the timesheet in a print-friendly format\"\"\"
    # Get the same parameters as the timesheet view
    year = request.args.get('year', data_processor.get_current_year())
    month = request.args.get('month', data_processor.get_current_month())
    dept_id = request.args.get('department', None)
    housing_id = request.args.get('housing', None)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Process and format timesheet data using the same function as the regular view
    try:
        timesheet_data = data_processor.generate_timesheet(year, month, dept_id, start_date, end_date, housing_id)
        if timesheet_data.get('total_employees', 0) == 0:
            logger.warning(f"No employees found for timesheet export: Year={year}, Month={month}, Dept={dept_id}, Housing={housing_id}")
    except Exception as e:
        logger.error(f"Error generating timesheet for export: {str(e)}")
        flash(f"Error exporting timesheet: {str(e)}", "danger")
        return redirect(url_for('timesheet', year=year, month=month, department=dept_id, housing=housing_id))
    
    # Get department name if specified
    department_name = _('all_departments')
    if dept_id:
        dept = Department.query.get(dept_id)
        if dept:
            department_name = dept.name
    
    # Get housing name if specified    housing_name = _('all_housings')
    if housing_id:
        housing = Housing.query.get(housing_id)
        if housing:
            housing_name = housing.name
    
    # Current date for the export
    current_date = datetime.now()
    report_id = f"{current_date.strftime('%y%m%d%H%M')}"
    
    # Render the professional PDF template
    return render_template(
        'timesheet_print.html',
        timesheet_data=timesheet_data,
        department_name=department_name,
        housing_name=housing_name,
        current_date=current_date,
        report_id=report_id
    )
    )
"""
        
        # Find a good position to add the new route - after the timesheet route
        timesheet_route_position = app_content.find('@app.route(\'/timesheet\')')
        if timesheet_route_position > 0:
            # Find the end of the timesheet function
            end_marker = app_content.find('def', timesheet_route_position + 20)
            end_position = app_content.rfind('return', timesheet_route_position, end_marker)
            end_position = app_content.find('\n', end_position)
            
            # Add the new route after the timesheet function
            updated_content = app_content[:end_position] + '\n' + new_route + app_content[end_position:]
            
            # Write the updated content back to the file
            with open(app_file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
                
            print("✅ Added new export_timesheet route to app.py")
            return True
        else:
            print("❌ Could not find the timesheet route in app.py")
            return False
    
    except Exception as e:
        print(f"❌ Error enhancing timesheet export: {str(e)}")
        return False

def update_timesheet_print_template():
    """Update the timesheet_print.html template to work with server-side rendering"""
    try:
        # Find the template file
        template_path = os.path.join(os.getcwd(), 'templates', 'timesheet_print.html')
        
        # Create updated template content
        updated_template = """<!DOCTYPE html>
<html lang="en" {% if get_locale() == 'ar' %}dir="rtl"{% endif %}>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ timesheet_data.month_name }} {{ timesheet_data.year }} - {{ t('monthly_timesheet') }}</title>
    <style>
        /* Base styles and reset */
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            margin: 0;
            padding: 0;
            color: #000;
            background: #fff;
        }

        /* Print-specific styles */
        @page {
            size: landscape;
            margin: 1.5cm;
        }

        /* Container styling */
        .print-container {
            width: 100%;
            background: #fff;
        }

        /* Header styling */
        .print-header {
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #2c3e50;
            position: relative;
        }

        .print-header .logo {
            height: 70px;
            position: absolute;
            {% if get_locale() == 'ar' %}
            right: 0;
            {% else %}
            left: 0;
            {% endif %}
            top: 0;
        }

        .print-header h1 {
            font-size: 24pt;
            color: #2c3e50;
            margin: 0;
            font-weight: 600;
        }

        .print-header h2 {
            font-size: 16pt;
            color: #3498db;
            font-weight: normal;
            margin: 5px 0 10px 0;
        }

        .print-header .info-container {
            display: flex;
            justify-content: space-between;
            font-size: 10pt;
            color: #555;
            margin-top: 10px;
        }

        .print-header .company-info {
            text-align: {% if get_locale() == 'ar' %}right{% else %}left{% endif %};
        }

        .print-header .timesheet-info {
            text-align: {% if get_locale() == 'ar' %}left{% else %}right{% endif %};
        }

        /* Table styling */
        .timesheet-print-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 9pt;
        }

        .timesheet-print-table th {
            background-color: #2c3e50;
            color: #fff;
            font-weight: 600;
            text-align: center;
            padding: 8px 4px;
            border: 1px solid #34495e;
        }

        .timesheet-print-table td {
            padding: 6px 4px;
            border: 1px solid #bdc3c7;
            text-align: center;
        }

        /* Employee header row */
        .employee-row {
            background-color: #ecf0f1;
            font-weight: bold;
        }

        /* Housing header row */
        .housing-header {
            background-color: #34495e;
            color: #fff;
            font-weight: bold;
            text-align: {% if get_locale() == 'ar' %}right{% else %}left{% endif %};
            padding: 6px 8px !important;
            font-size: 11pt;
        }

        /* Alternating row colors */
        .timesheet-print-table tr:nth-child(even):not(.housing-header) {
            background-color: #f9f9f9;
        }

        /* Status colors with better visibility */
        .status-P {
            background-color: #e8f5e9 !important;
            color: #1b5e20;
        }

        .status-A {
            background-color: #ffebee !important;
            color: #b71c1c;
        }

        .status-V {
            background-color: #e3f2fd !important;
            color: #0d47a1;
        }

        .status-T {
            background-color: #e8f5e9 !important;
            color: #1b5e20;
            font-style: italic;
        }

        .status-S {
            background-color: #fff8e1 !important;
            color: #ff6f00;
        }

        .status-E {
            background-color: #e0f7fa !important; 
            color: #006064;
        }

        .status-W {
            background-color: #f5f5f5 !important;
            color: #424242;
        }

        /* Weekend column styling */
        .weekend-day {
            background-color: #ecf0f1;
            font-weight: bold;
        }

        /* Total columns styling */
        .total-column {
            background-color: #e1f5fe !important;
            color: #01579b;
            font-weight: bold;
        }

        /* Footer styling */
        .print-footer {
            margin-top: 20px;
            border-top: 1px solid #bdc3c7;
            padding-top: 10px;
            font-size: 9pt;
            color: #7f8c8d;
            display: flex;
            justify-content: space-between;
        }

        .print-footer .page-info {
            text-align: {% if get_locale() == 'ar' %}left{% else %}right{% endif %};
        }

        /* Status legend */
        .status-legend {
            margin-top: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            font-size: 9pt;
        }

        .status-legend-item {
            display: flex;
            align-items: center;
        }

        .status-legend-color {
            width: 16px;
            height: 16px;
            margin-right: 5px;
            border: 1px solid #bdc3c7;
        }

        /* Signature section */
        .signature-section {
            margin-top: 30px;
            display: flex;
            justify-content: space-between;
        }

        .signature-box {
            width: 30%;
            text-align: center;
        }

        .signature-line {
            border-top: 1px solid #000;
            padding-top: 5px;
            margin-top: 40px;
        }

        /* RTL specific adjustments */
        {% if get_locale() == 'ar' %}
        body {
            font-family: 'Segoe UI', 'Arial', 'Tahoma', sans-serif;
        }
        {% endif %}

        /* Print optimization */
        @media print {
            body {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            
            .timesheet-print-table {
                page-break-inside: auto;
            }
            
            .timesheet-print-table tr {
                page-break-inside: avoid;
                page-break-after: auto;
            }
            
            .timesheet-print-table thead {
                display: table-header-group;
            }
            
            .timesheet-print-table tfoot {
                display: table-footer-group;
            }
        }
    </style>
</head>
<body>
    <div class="print-container">
        <div class="print-header">
            <img src="{{ url_for('static', filename='img/company-logo.svg') }}" alt="Company Logo" class="logo">
            <h1>{{ t('monthly_timesheet') }}</h1>
            <h2>{{ month_name }} {{ year }}</h2>
            
            <div class="info-container">
                <div class="company-info">
                    <div><strong>{{ t('department') }}:</strong> {{ department_name }}</div>
                    <div><strong>{{ t('housing') }}:</strong> {{ housing_name }}</div>
                    <div><strong>{{ t('period') }}:</strong> {{ period_text }}</div>
                </div>
                <div class="timesheet-info">
                    <div><strong>{{ t('generated') }}:</strong> {{ export_date }}</div>
                    <div><strong>{{ t('report_id') }}:</strong> {{ report_id }}</div>
                </div>
            </div>
        </div>
        
        <!-- Timesheet table -->
        <table class="timesheet-print-table">
            <thead>
                <tr class="text-center">
                    <th rowspan="2" class="text-center align-middle">{{ t('employee_code') }}</th>
                    <th rowspan="2" class="text-center align-middle">{{ t('name') }}</th>
                    <th rowspan="2" class="text-center align-middle">{{ t('profession') }}</th>
                    
                    <!-- Dates header -->
                    {% for date in timesheet_data.dates %}
                        <th class="text-center {% if date.weekday() in timesheet_data.weekend_days %}weekend-day{% endif %}">
                            {{ date.day }}
                        </th>
                    {% endfor %}
                    
                    <!-- Total columns -->
                    <th rowspan="2" class="text-center align-middle total-column">{{ t('regular_hours') }}</th>
                    <th rowspan="2" class="text-center align-middle total-column">{{ t('overtime') }}</th>
                </tr>
                <tr class="text-center">
                    <!-- Weekday header -->
                    {% for date in timesheet_data.dates %}
                        <th class="text-center small {% if date.weekday() in timesheet_data.weekend_days %}weekend-day{% endif %}">
                            {{ date.strftime('%a') }}
                        </th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% set housing_groups = {} %}
                
                <!-- Group employees by housing instead of device -->
                {% for employee in timesheet_data.employees %}
                    {% set housing = employee.housing|default('Unknown Housing') %}
                    {% if housing not in housing_groups %}
                        {% set _ = housing_groups.update({housing: []}) %}
                    {% endif %}
                    {% set _ = housing_groups[housing].append(employee) %}
                {% endfor %}
                
                <!-- Display employees grouped by housing -->
                {% for housing, employees in housing_groups.items() %}
                    <!-- Housing header row -->
                    <tr>
                        <td colspan="{{ 3 + timesheet_data.dates|length + 2 }}" class="housing-header">
                            {{ housing }}
                        </td>
                    </tr>
                    
                    <!-- Employees for this housing -->
                    {% for employee in employees %}
                        <tr {% if loop.index is even %}class="even-row"{% endif %}>
                            <td>{{ employee.employee_code }}</td>
                            <td>{{ employee.name }}</td>
                            <td>{{ employee.profession|default('') }}</td>
                            
                            <!-- Attendance cells -->
                            {% for date in timesheet_data.dates %}
                                {% set day = date.strftime('%Y-%m-%d') %}
                                {% set attendance = employee.attendance.get(day, {}) %}
                                {% set status = attendance.get('status', '') %}
                                {% set value = attendance.get('value', '') %}
                                
                                <td class="status-{{ status }}">{{ value }}</td>
                            {% endfor %}
                            
                            <!-- Totals -->
                            <td class="total-column">{{ employee.totals.regular_hours }}</td>
                            <td class="total-column">{{ employee.totals.overtime }}</td>
                        </tr>
                    {% endfor %}
                {% endfor %}
            </tbody>
        </table>
        
        <div class="status-legend">
            <div class="status-legend-item">
                <div class="status-legend-color status-P"></div>
                <div>{{ t('present') }} (P)</div>
            </div>
            <div class="status-legend-item">
                <div class="status-legend-color status-A"></div>
                <div>{{ t('absent') }} (A)</div>
            </div>
            <div class="status-legend-item">
                <div class="status-legend-color status-V"></div>
                <div>{{ t('vacation') }} (V)</div>
            </div>
            <div class="status-legend-item">
                <div class="status-legend-color status-S"></div>
                <div>{{ t('sick') }} (S)</div>
            </div>
            <div class="status-legend-item">
                <div class="status-legend-color status-W"></div>
                <div>{{ t('weekend') }} (W)</div>
            </div>
            <div class="status-legend-item">
                <div class="status-legend-color status-T"></div>
                <div>{{ t('transfer') }} (T)</div>
            </div>
        </div>
        
        <div class="signature-section">
            <div class="signature-box">
                <div class="signature-line">{{ t('prepared_by') }}</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{ t('approved_by') }}</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">{{ t('department_manager') }}</div>
            </div>
        </div>
        
        <div class="print-footer">
            <div>{{ t('housing_maintenance_system') }} - {{ t('monthly_timesheet') }}</div>
            <div class="page-info">{{ t('page') }} 1 {{ t('of') }} 1</div>
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
"""
        
        # Write the updated template to the file
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(updated_template)
            
        print("✅ Updated the timesheet_print.html template")
        return True
            
    except Exception as e:
        print(f"❌ Error updating timesheet_print.html template: {str(e)}")
        return False

def update_timesheet_button():
    """Update the export button in the timesheet.html to use the new route"""
    try:
        # Find the template file
        template_path = os.path.join(os.getcwd(), 'templates', 'timesheet.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Find the export button
        old_button = '<button class="btn btn-sm btn-success" id="export-pdf">\n    <i class="fas fa-file-pdf"></i> Export PDF\n</button>'
        
        # Create a new button that links to the export route
        new_button = """<a href="{{ url_for('export_timesheet', year=selected_year, month=selected_month, department=selected_dept, housing=selected_housing) }}" class="btn btn-sm btn-success">
    <i class="fas fa-file-pdf"></i> Export PDF
</a>"""
        
        # Replace the button
        updated_content = template_content.replace(old_button, new_button)
        
        # Write the updated content back to the file
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        print("✅ Updated the export button in timesheet.html")
        return True
        
    except Exception as e:
        print(f"❌ Error updating export button: {str(e)}")
        return False

def update_translations():
    """Add new translations for PDF export labels"""
    try:
        # Find the translations file
        translations_path = os.path.join(os.getcwd(), 'translations.py')
        
        with open(translations_path, 'r', encoding='utf-8') as f:
            translations_content = f.read()
        
        # Locate the English section for timesheet page
        en_timesheet_section_pos = translations_content.find('# Timesheet page')
        
        # New translations for English
        new_en_translations = """        'generated': 'Generated',
        'report_id': 'Report ID',
        'period': 'Period',
        'page': 'Page',
        'of': 'of',
        'employee_code': 'C No.',
        'name': 'NAME',
        'profession': 'Profession',
        'regular_hours': 'Regular Hours',
        'overtime': 'Overtime',
        'present': 'Present',
        'absent': 'Absent',
        'vacation': 'Vacation',
        'sick': 'Sick',
        'weekend': 'Weekend',
        'transfer': 'Transfer',
        'prepared_by': 'Prepared By',
        'approved_by': 'Approved By',
        'department_manager': 'Department Manager',
        'housing_maintenance_system': 'Housing Maintenance System',"""
        
        # Insert the new English translations
        if en_timesheet_section_pos > 0:
            en_insert_pos = translations_content.find('\n', en_timesheet_section_pos) + 1
            updated_content = translations_content[:en_insert_pos] + new_en_translations + '\n' + translations_content[en_insert_pos:]
            
            # Locate the Arabic section for timesheet page
            ar_timesheet_section_pos = updated_content.find('# Timesheet page', en_timesheet_section_pos + 100)
            
            # New translations for Arabic
            new_ar_translations = """        'generated': 'تاريخ الإنشاء',
        'report_id': 'رقم التقرير',
        'period': 'الفترة',
        'page': 'صفحة',
        'of': 'من',
        'employee_code': 'الرقم',
        'name': 'الإسم',
        'profession': 'المهنة',
        'regular_hours': 'الساعات العادية',
        'overtime': 'الساعات الإضافية',
        'present': 'حاضر',
        'absent': 'غائب',
        'vacation': 'إجازة',
        'sick': 'مريض',
        'weekend': 'عطلة نهاية الأسبوع',
        'transfer': 'نقل',
        'prepared_by': 'إعداد',
        'approved_by': 'اعتماد',
        'department_manager': 'مدير القسم',
        'housing_maintenance_system': 'نظام صيانة الإسكان',"""
            
            # Insert the Arabic translations
            if ar_timesheet_section_pos > 0:
                ar_insert_pos = updated_content.find('\n', ar_timesheet_section_pos) + 1
                updated_content = updated_content[:ar_insert_pos] + new_ar_translations + '\n' + updated_content[ar_insert_pos:]
                
                # Write the updated translations
                with open(translations_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                    
                print("✅ Added new translations for PDF export")
                return True
            else:
                print("❌ Could not find Arabic timesheet section in translations.py")
                return False
        else:
            print("❌ Could not find English timesheet section in translations.py")
            return False
        
    except Exception as e:
        print(f"❌ Error updating translations: {str(e)}")
        return False

if __name__ == "__main__":
    print("Enhancing timesheet PDF export...")
    
    # Step 1: Add the new route to app.py
    enhance_timesheet_export()
    
    # Step 2: Update the timesheet_print.html template
    update_timesheet_print_template()
    
    # Step 3: Update the export button in timesheet.html
    update_timesheet_button()
    
    # Step 4: Add new translations
    update_translations()
    
    print("\nTimesheet PDF export enhancement complete! 🎉")
    print("Restart the application to apply changes.")
    print("The timesheet will now be exported with a professional design and formatting.")
