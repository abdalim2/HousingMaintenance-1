import requests

def test_api_endpoint():
    response = requests.get('http://example.com/api/endpoint')
    assert response.status_code == 200
    assert 'expected_data' in response.json()

def test_authentication():
    response = requests.post('http://example.com/api/auth', json={'username': 'valid_user', 'password': 'valid_pass'})
    assert response.status_code == 200
    assert 'token' in response.json()

    response = requests.post('http://example.com/api/auth', json={'username': 'invalid_user', 'password': 'invalid_pass'})
    assert response.status_code == 401