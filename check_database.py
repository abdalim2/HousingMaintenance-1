import sqlite3
import os

# التحقق من المسار الحالي
print(f"المسار الحالي: {os.getcwd()}")

# فتح قاعدة البيانات
conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# استعلام للحصول على قائمة الجداول
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("الجداول المتاحة في قاعدة البيانات:")
for table in tables:
    print(f"- {table[0]}")

# التحقق من سجلات الحضور لتاريخ 11-5-2025
print("\nالتحقق من سجلات الحضور ليوم 11-5-2025:")
try:
    cursor.execute("SELECT * FROM attendance_records WHERE date = '2025-05-11' LIMIT 5")
    records = cursor.fetchall()
    print(f"عدد السجلات: {len(records)}")
    
    # عرض أسماء الأعمدة
    column_names = [description[0] for description in cursor.description]
    print(f"الأعمدة: {column_names}")
    
    # عرض السجلات
    for record in records:
        print(record)
except Exception as e:
    print(f"خطأ: {e}")

# التحقق من سجلات المزامنة
print("\nالتحقق من سجلات المزامنة:")
try:
    # استعلام عن اسم جدول سجلات المزامنة
    for possible_table in ['sync_logs', 'sync_log', 'synclogs', 'synclog']:
        cursor.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{possible_table}'")
        if cursor.fetchone()[0] > 0:
            print(f"جدول المزامنة الموجود: {possible_table}")
            
            # استعلام عن آخر سجلات المزامنة
            cursor.execute(f"SELECT * FROM {possible_table} ORDER BY id DESC LIMIT 3")
            logs = cursor.fetchall()
            
            # عرض أسماء الأعمدة
            column_names = [description[0] for description in cursor.description]
            print(f"الأعمدة: {column_names}")
            
            # عرض السجلات
            for log in logs:
                print(log)
            
            break
    else:
        print("لم يتم العثور على جدول المزامنة")
except Exception as e:
    print(f"خطأ: {e}")

# إغلاق الاتصال
conn.close()
