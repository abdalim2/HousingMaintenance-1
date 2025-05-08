from app import app
from models import db, SyncLog

with app.app_context():
    # Get the latest sync log
    latest_sync = SyncLog.query.order_by(SyncLog.id.desc()).first()
    if latest_sync:
        print(f'Latest sync (ID: {latest_sync.id}):')
        print(f'Time: {latest_sync.sync_time}')
        print(f'Status: {latest_sync.status}')
        print(f'Step: {latest_sync.step}')
        print(f'Progress: {latest_sync.progress}')
        print(f'Message: {latest_sync.message}')
        print(f'Error: {latest_sync.error}')
        print(f'Records synced: {latest_sync.records_synced}')
    else:
        print('No sync logs found')
