from app import app
from sync_service import start_sync_in_background

with app.app_context():
    result = start_sync_in_background(app)
    print(f'Sync started: {result}')
