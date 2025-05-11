from database import db
from models import SyncLog, AttendanceRecord
from flask import Flask
import datetime

app = Flask(__name__)
# استخدام نفس اتصال قاعدة البيانات كما في التطبيق الرئيسي
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
db.init_app(app)

with app.app_context():
    # التحقق من آخر عمليات المزامنة
    logs = SyncLog.query.order_by(SyncLog.id.desc()).limit(3).all()
    print('آخر 3 عمليات مزامنة:')
    for log in logs:
        print(f'ID: {log.id}, التاريخ: {log.sync_time}, الحالة: {log.status}, السجلات: {log.records_synced}')
    
    # التحقق من سجلات الحضور لتاريخ 11-5-2025
    target_date = datetime.date(2025, 5, 11)
    records = AttendanceRecord.query.filter(AttendanceRecord.date == target_date).all()
    print(f'\\nسجلات الحضور ليوم 11-5-2025: {len(records)}')
    for rec in records[:5]:  # عرض أول 5 سجلات فقط
        print(f'الموظف: {rec.employee_id}, التاريخ: {rec.date}, الحالة: {rec.attendance_status}, الدخول: {rec.clock_in}, الخروج: {rec.clock_out}')
