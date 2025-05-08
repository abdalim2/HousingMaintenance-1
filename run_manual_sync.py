from app import app
from models import db, SyncLog, AttendanceRecord
from sync_service import start_sync_in_background
from datetime import datetime, date

with app.app_context():
    try:
        # Start a manual sync
        print("Starting manual sync...")
        result = start_sync_in_background(app)
        print(f"Sync started: {result}")
        
        # Let's check if it worked after waiting
        print("Waiting for sync to complete... (this might not show completion in this script)")
        
        # Verify that we have at least one synced record
        synced_records = AttendanceRecord.query.filter_by(is_synced=True).count()
        print(f"Currently have {synced_records} synced attendance records")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
