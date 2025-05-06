from pytest import fixture

@fixture
def client():
    from flask import Flask
    app = Flask(__name__)

    with app.test_client() as client:
        yield client

def test_link_and_auth(client):
    response = client.get('/api/some_endpoint')
    assert response.status_code == 200
    assert 'expected_data' in response.get_json()