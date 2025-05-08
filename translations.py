"""
Translation dictionaries for BiometricSync application
Supports English and Arabic languages
"""

# Define translations
translations = {
    'en': {
        # Navigation
        'app_title': 'Attendance Tracking System',
        'dashboard': 'Dashboard',
        'monthly_timesheet': 'Monthly Timesheet',
        'departments': 'Departments',
        'settings': 'Settings',
        'sync_status': 'BioTime Sync Status',
        'connected': 'Connected',
        'disconnected': 'Disconnected',
        
        # Settings page
        'biotime_settings': 'BioTime API Settings',
        'api_url': 'API URL',
        'username': 'Username',
        'password': 'Password',
        'sync_interval': 'Sync Interval (hours)',
        'sync_now': 'Save & Sync Now',
        'last_sync': 'Last Sync',
        'status': 'Status',
        'records_synced': 'Records Synced',
        'departments': 'Departments',
        'date_range': 'Date Range',
        'start_date': 'Start Date',
        'end_date': 'End Date',
        'display_settings': 'Display Settings',
        'default_view': 'Default View',
        'current_month': 'Current Month',
        'previous_month': 'Previous Month',
        'weekend_days': 'Weekend Days',
        'friday': 'Friday',
        'saturday': 'Saturday',
        'sunday': 'Sunday',
        'language': 'Language',
        'english': 'English',
        'arabic': 'Arabic',
        'save_settings': 'Save Settings',
        
        # Timesheet page
        'timesheet_title': 'Monthly Timesheet',
        'department': 'Department',
        'all_departments': 'All Departments',
        'month': 'Month',
        'year': 'Year',
        'view': 'View',
        'present': 'Present',
        'absent': 'Absent',
        'vacation': 'Vacation',
        'transfer': 'Transfer',
        'sick': 'Sick',
        'eid': 'Eid',
        
        # Departments page
        'departments_management': 'Departments Management',
        'departments_list': 'Departments List',
        'add_department': 'Add Department',
        'edit_department': 'Edit Department',
        'delete_department': 'Delete Department',
        'department_name': 'Department Name',
        'biotime_id': 'BioTime ID',
        'biotime_id_help_text': 'Enter the department ID as it appears in BioTime system',
        'employees': 'Employees',
        'active': 'Active',
        'inactive': 'Inactive',
        'actions': 'Actions',
        'is_active': 'Is Active',
        'update': 'Update',
        'no_departments_found': 'No departments found',
        'delete_department_confirmation': 'Are you sure you want to delete department',
        'department_has_employees': 'This department has employees',
        'move_employees_first': 'Please move employees to another department first',
        'name': 'Name',
        
        # Department details page
        'department_details': 'Department Details',
        'basic_info': 'Basic Information',
        'department_id': 'Department ID',
        'employees_count': 'Number of Employees',
        'department_statistics': 'Department Statistics',
        'department_employees': 'Department Employees',
        'search_employees': 'Search Employees',
        'employee_code': 'Employee Code',
        'profession': 'Profession',
        'housing': 'Housing',
        'view_details': 'View Details',
        'close': 'Close',
        'department_performance': 'Department Performance',
        'loading': 'Loading',
        'loading_employees': 'Loading employees',
        'loading_statistics': 'Loading statistics',
        'no_employees_found': 'No employees found in this department',
        'error_loading_employees': 'Error loading employees',
        'error_loading_statistics': 'Error loading statistics',
        'attendance_last_30_days': 'Attendance distribution for the last 30 days',
        
        # Employee Status Management
        'employee_status': 'Employee Status',
        'employee_vacations': 'Employee Vacations',
        'employee_transfers': 'Employee Transfers',
        'add_vacation': 'Add Vacation',
        'add_transfer': 'Add Transfer',
        'edit_vacation': 'Edit Vacation',
        'edit_transfer': 'Edit Transfer',
        'delete_vacation': 'Delete Vacation',
        'delete_transfer': 'Delete Transfer',
        'employee': 'Employee',
        'select_employee': 'Select Employee',
        'notes': 'Notes',
        'from_to': 'From → To',
        'transfer_type': 'Transfer Type',
        'department_transfer': 'Department Transfer',
        'housing_transfer': 'Housing Transfer',
        'from_department': 'From Department',
        'to_department': 'To Department',
        'from_housing': 'From Housing',
        'to_housing': 'To Housing',
        'select_department': 'Select Department',
        'select_housing': 'Select Housing',
        'confirm_delete_vacation': 'Are you sure you want to delete this vacation?',
        'confirm_delete_transfer': 'Are you sure you want to delete this transfer?',
        'vacation_info': 'Vacation periods will be marked with "V" in the timesheet.',
        'transfer_info': 'Transfer periods will be marked with "T" in the timesheet.',
        'please_select_departments': 'Please select at least one department',
        'please_select_housings': 'Please select at least one housing location',
        'no_vacations': 'No vacations found',
        'no_transfers': 'No transfers found',
        'transfer_data': 'Transfer data',
        
        # Common
        'save': 'Save',
        'cancel': 'Cancel',
        'delete': 'Delete',
        'edit': 'Edit',
        'add': 'Add',
        'search': 'Search',
        'filter': 'Filter'
    },
    'ar': {
        # Navigation
        'app_title': 'نظام تتبع الحضور',
        'dashboard': 'لوحة التحكم',
        'monthly_timesheet': 'الجدول الشهري',
        'departments': 'الأقسام',
        'settings': 'الإعدادات',
        'sync_status': 'حالة المزامنة',
        'connected': 'متصل',
        'disconnected': 'غير متصل',
        
        # Settings page
        'biotime_settings': 'إعدادات BioTime API',
        'api_url': 'رابط API',
        'username': 'اسم المستخدم',
        'password': 'كلمة المرور',
        'sync_interval': 'فترة المزامنة (ساعات)',
        'sync_now': 'حفظ ومزامنة الآن',
        'last_sync': 'آخر مزامنة',
        'status': 'الحالة',
        'records_synced': 'السجلات المتزامنة',
        'departments': 'الأقسام',
        'date_range': 'نطاق التاريخ',
        'start_date': 'تاريخ البدء',
        'end_date': 'تاريخ الانتهاء',
        'display_settings': 'إعدادات العرض',
        'default_view': 'العرض الافتراضي',
        'current_month': 'الشهر الحالي',
        'previous_month': 'الشهر السابق',
        'weekend_days': 'أيام نهاية الأسبوع',
        'friday': 'الجمعة',
        'saturday': 'السبت',
        'sunday': 'الأحد',
        'language': 'اللغة',
        'english': 'الإنجليزية',
        'arabic': 'العربية',
        'save_settings': 'حفظ الإعدادات',
        
        # Timesheet page
        'timesheet_title': 'الجدول الزمني الشهري',
        'department': 'القسم',
        'all_departments': 'جميع الأقسام',
        'month': 'الشهر',
        'year': 'السنة',
        'view': 'عرض',
        'present': 'حاضر',
        'absent': 'غائب',
        'vacation': 'إجازة',
        'transfer': 'نقل',
        'sick': 'مرضي',
        'eid': 'عيد',
        
        # Departments page
        'departments_management': 'إدارة الأقسام',
        'departments_list': 'قائمة الأقسام',
        'add_department': 'إضافة قسم',
        'edit_department': 'تعديل قسم',
        'delete_department': 'حذف قسم',
        'department_name': 'اسم القسم',
        'biotime_id': 'معرف النظام',
        'biotime_id_help_text': 'أدخل معرف القسم كما يظهر في نظام البصمة',
        'employees': 'الموظفون',
        'active': 'نشط',
        'inactive': 'غير نشط',
        'actions': 'الإجراءات',
        'is_active': 'نشط',
        'update': 'تحديث',
        'no_departments_found': 'لم يتم العثور على أقسام',
        'delete_department_confirmation': 'هل أنت متأكد من حذف القسم',
        'department_has_employees': 'هذا القسم يحتوي على موظفين',
        'move_employees_first': 'الرجاء نقل الموظفين إلى قسم آخر أولاً',
        'name': 'الاسم',
        
        # Department details page
        'department_details': 'تفاصيل القسم',
        'basic_info': 'المعلومات الأساسية',
        'department_id': 'رقم القسم',
        'employees_count': 'عدد الموظفين',
        'department_statistics': 'إحصائيات القسم',
        'department_employees': 'موظفي القسم',
        'search_employees': 'بحث عن الموظفين',
        'employee_code': 'رقم الموظف',
        'profession': 'المهنة',
        'housing': 'السكن',
        'view_details': 'عرض التفاصيل',
        'close': 'إغلاق',
        'department_performance': 'أداء القسم',
        'loading': 'جاري التحميل',
        'loading_employees': 'جاري تحميل قائمة الموظفين',
        'loading_statistics': 'جاري تحميل الإحصائيات',
        'no_employees_found': 'لا يوجد موظفين في هذا القسم',
        'error_loading_employees': 'خطأ في تحميل بيانات الموظفين',
        'error_loading_statistics': 'خطأ في تحميل الإحصائيات',
        'attendance_last_30_days': 'توزيع الحضور خلال الـ 30 يوم الماضية',
        
        # Employee Status Management
        'employee_status': 'حالة الموظفين',
        'employee_vacations': 'إجازات الموظفين',
        'employee_transfers': 'تحويلات الموظفين',
        'add_vacation': 'إضافة إجازة',
        'add_transfer': 'إضافة تحويل',
        'edit_vacation': 'تعديل الإجازة',
        'edit_transfer': 'تعديل التحويل',
        'delete_vacation': 'حذف الإجازة',
        'delete_transfer': 'حذف التحويل',
        'employee': 'الموظف',
        'select_employee': 'اختر موظف',
        'notes': 'ملاحظات',
        'from_to': 'من ← إلى',
        'transfer_type': 'نوع التحويل',
        'department_transfer': 'تحويل قسم',
        'housing_transfer': 'تحويل سكن',
        'from_department': 'من قسم',
        'to_department': 'إلى قسم',
        'from_housing': 'من سكن',
        'to_housing': 'إلى سكن',
        'select_department': 'اختر قسم',
        'select_housing': 'اختر سكن',
        'confirm_delete_vacation': 'هل أنت متأكد من حذف هذه الإجازة؟',
        'confirm_delete_transfer': 'هل أنت متأكد من حذف هذا التحويل؟',
        'vacation_info': 'سيتم تمييز فترات الإجازة بعلامة "V" في جدول الوقت.',
        'transfer_info': 'سيتم تمييز فترات التحويل بعلامة "T" في جدول الوقت.',
        'please_select_departments': 'يرجى اختيار قسم واحد على الأقل',
        'please_select_housings': 'يرجى اختيار سكن واحد على الأقل',
        'no_vacations': 'لم يتم العثور على إجازات',
        'no_transfers': 'لم يتم العثور على تحويلات',
        'transfer_data': 'بيانات التحويل',
        
        # Common
        'save': 'حفظ',
        'cancel': 'إلغاء',
        'delete': 'حذف',
        'edit': 'تعديل',
        'add': 'إضافة',
        'search': 'بحث',
        'filter': 'تصفية'
    }
}

def get_text(key, language='en'):
    """
    Get translated text for the given key in the specified language
    Falls back to English if translation not found
    
    Args:
        key: The translation key
        language: The language code ('en' or 'ar')
        
    Returns:
        str: Translated text
    """
    if language not in translations:
        language = 'en'
        
    if key in translations[language]:
        return translations[language][key]
    elif key in translations['en']:
        # Fallback to English if key not found in selected language
        return translations['en'][key]
    else:
        # Return the key itself if not found in any language
        return key