"""
Test script to verify that the AttendanceRecord model has the is_synced and sync_id columns.
"""
from models import AttendanceRecord, db

def test_model_columns():
    """Test that the AttendanceRecord model has the is_synced and sync_id columns."""
    # Get the table columns
    columns = AttendanceRecord.__table__.columns
    
    # Check if is_synced and sync_id exist
    is_synced_exists = 'is_synced' in columns
    sync_id_exists = 'sync_id' in columns
    
    print(f"is_synced exists: {is_synced_exists}")
    print(f"sync_id exists: {sync_id_exists}")
    
    # Print all columns for verification
    print("\nAll columns in AttendanceRecord model:")
    for column in columns:
        print(f" - {column.name}")

if __name__ == "__main__":
    test_model_columns()
