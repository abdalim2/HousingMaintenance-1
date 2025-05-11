import traceback
from flask import Flask, request, session

try:
    from app import app
    from data_processor import generate_timesheet
    
    # Create a test request context
    with app.test_request_context('/timesheet'), app.app_context():
        # Initialize session variables that might be needed
        session['language'] = 'en'
        
        # Run the function with the error
        result = generate_timesheet('2025', '5', force_refresh=True)
        print('Timesheet generated successfully' if result else 'Failed to generate timesheet')
except Exception as e:
    traceback.print_exc()
    print(f'Error: {e}')
