from app import app
from models import db, SyncLog

with app.app_context():
    # Get all sync logs, ordered by ID
    sync_logs = SyncLog.query.order_by(SyncLog.id.desc()).all()
    print(f'Found {len(sync_logs)} sync logs:')
    
    for log in sync_logs:
        print(f'\nSync log ID: {log.id}:')
        print(f'Time: {log.sync_time}')
        print(f'Status: {log.status}')
        print(f'Step: {log.step}')
        print(f'Progress: {log.progress}')
        print(f'Message: {log.message}')
        print(f'Error: {log.error}')
        print(f'Records synced: {log.records_synced}')
