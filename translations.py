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