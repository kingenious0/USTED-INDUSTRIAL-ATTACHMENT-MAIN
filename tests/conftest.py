import os
import shutil
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.student_master import StudentMaster
from app.utils.seed_data import seed_database


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    test_app = create_app('testing')

    with test_app.app_context():
        db.create_all()
        seed_database()
        yield test_app
        db.session.remove()
        db.drop_all()

    # Clean up test uploads directory if created
    test_upload_dir = test_app.config['UPLOAD_FOLDER']
    if os.path.exists(test_upload_dir):
        shutil.rmtree(test_upload_dir)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return test_app_client(app)


def test_app_client(app):
    return app.test_client()


class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, username='student1', password='password123'):
        return self._client.post(
            '/auth/login',
            data={'username': username, 'password': password},
            follow_redirects=True
        )

    def logout(self):
        return self._client.get('/auth/logout', follow_redirects=True)


@pytest.fixture
def auth(client):
    return AuthActions(client)
