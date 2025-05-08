from app import app
from models import db, SyncLog
from datetime import datetime

with app.app_context():
    try:
        # Create a test SyncLog entry
        new_sync_log = SyncLog(
            sync_time=datetime.utcnow(),
            status="testing",
            step="test",
            progress=100,
            message="This is a test entry to verify SyncLog is working",
            error=None,
            departments_synced="10",
            records_synced=0
        )
        db.session.add(new_sync_log)
        db.session.commit()
        print(f"Successfully created test SyncLog with ID: {new_sync_log.id}")
        
        # Verify by reading back
        sync_log = SyncLog.query.get(new_sync_log.id)
        print(f"Retrieved: ID {sync_log.id}, Status: {sync_log.status}, Message: {sync_log.message}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
