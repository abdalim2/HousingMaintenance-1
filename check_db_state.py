from app import app
from models import db, AttendanceRecord, SyncLog, MonthPeriod, TempAttendance, BiometricTerminal

with app.app_context():
    print('AttendanceRecord entries:', AttendanceRecord.query.count())
    print('SyncLog entries:', SyncLog.query.count())
    print('Synced records:', AttendanceRecord.query.filter_by(is_synced=True).count())
    print('BiometricTerminal entries:', BiometricTerminal.query.count())
    print('MonthPeriod entries:', MonthPeriod.query.count())
    print('TempAttendance entries:', TempAttendance.query.count())
    
    # Check the structure of the AttendanceRecord table
    attendance_record = AttendanceRecord.query.first()
    if attendance_record:
        print('\nAttendanceRecord has fields:')
        for column in AttendanceRecord.__table__.columns:
            print(f'- {column.name}: {getattr(attendance_record, column.name, None)}')
    
    # Check the structure of the SyncLog table
    sync_log = SyncLog.query.first()
    if sync_log:
        print('\nSyncLog has fields:')
        for column in SyncLog.__table__.columns:
            print(f'- {column.name}: {getattr(sync_log, column.name, None)}')
