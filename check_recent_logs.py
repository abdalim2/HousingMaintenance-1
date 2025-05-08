from app import app
from models import db, SyncLog
from datetime import datetime, timedelta

with app.app_context():
    now = datetime.utcnow()
    five_minutes_ago = now - timedelta(minutes=5)
    
    # Get any sync logs from the past 5 minutes
    recent_logs = SyncLog.query.filter(SyncLog.sync_time >= five_minutes_ago).order_by(SyncLog.id.desc()).all()
    
    print(f'Found {len(recent_logs)} recent sync logs (within past 5 minutes):')
    
    for log in recent_logs:
        print(f'\nSync log ID: {log.id}:')
        print(f'Time: {log.sync_time}')
        print(f'Status: {log.status}')
        print(f'Step: {log.step}')
        print(f'Progress: {log.progress}')
        print(f'Message: {log.message}')
        print(f'Error: {log.error}')
        print(f'Records synced: {log.records_synced}')
