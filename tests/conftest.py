import pytest

@pytest.fixture(scope='session')
def test_client():
    from myapp import create_app
    app = create_app()
    with app.test_client() as client:
        yield client