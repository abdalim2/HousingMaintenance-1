from app import app
from models import db, SyncLog

with app.app_context():
    # Get the latest sync log with an error status
    error_logs = SyncLog.query.filter_by(status='error').order_by(SyncLog.id.desc()).all()
    
    if error_logs:
        for log in error_logs:
            print(f'\nError sync log ID: {log.id}:')
            print(f'Time: {log.sync_time}')
            print(f'Status: {log.status}')
            print(f'Step: {log.step}')
            print(f'Progress: {log.progress}')
            print(f'Message: {log.message}')
            print(f'Error: {log.error}')
            print(f'Records synced: {log.records_synced}')
    else:
        print('No error logs found')
