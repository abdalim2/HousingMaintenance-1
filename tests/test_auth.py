import requests
import pytest
from urllib.parse import quote

def test_bio_attendance_auth():
    """Test authentication and data retrieval from bioAttendance API"""
    # Credentials
    username = 'raghad'
    password = 'A1111111'
    
    # Base URL
    base_url = "http://213.210.196.115:8585/att/api/transactionReport/export/"
    
    # Parameters
    params = {
        'export_headers': 'emp_code,first_name,dept_name,att_date,punch_time,punch_state,terminal_alias',
        'start_date': '2025-04-01 00:00:00',
        'end_date': '2025-04-02 23:59:59',
        'departments': '10',
        'employees': '-1',
        'page_size': '6000',
        'export_type': 'txt',
        'page': '1',
        'limit': '6000'
    }
    
    # Create session to maintain cookies
    session = requests.Session()
    
    # First authenticate
    auth_url = base_url.replace('/transactionReport/export/', '/login')
    auth_data = {'username': username, 'password': password}
    
    auth_response = session.post(auth_url, json=auth_data)
    assert auth_response.status_code == 200, f"Authentication failed: {auth_response.text}"
    
    # Now get the report data using the authenticated session
    response = session.get(base_url, params=params)
    
    # Assert response is successful
    assert response.status_code == 200, f"API call failed: {response.text}"
    
    # Assert data is returned
    assert len(response.text) > 0, "No data returned from API"
    
    # Print first few lines of response for debugging
    print(f"Response preview: {response.text[:200]}...")
    
    # Additional checks you might want
    if response.headers.get('Content-Type') == 'application/json':
        data = response.json()
        assert 'data' in data, "Expected 'data' field in response"
    
    return response.text

# Optional - allow running this test directly
if __name__ == "__main__":
    result = test_bio_attendance_auth()
    print(f"Test completed successfully. Data length: {len(result)} characters")