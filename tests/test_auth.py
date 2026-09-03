from app.models.user import User


def test_login_student(client, auth):
    res = auth.login('student1', 'password123')
    assert res.status_code == 200
    assert b"Student Attachment Workspace" in res.data
    assert b"Kofi Mensah Boateng" in res.data


def test_login_liaison(client, auth):
    res = auth.login('liaison1', 'password123')
    assert res.status_code == 200
    assert b"Industrial Liaison Unit Dashboard" in res.data


def test_login_invalid_password(client, auth):
    res = auth.login('student1', 'wrongpassword')
    assert res.status_code == 200
    assert b"Invalid username or password" in res.data


def test_student_blocked_from_liaison_endpoints(client, auth):
    """PRD Section 11: Students cannot access administrative/liaison functions."""
    auth.login('student1', 'password123')
    res = client.get('/liaison/dashboard')
    assert res.status_code == 403
    assert b"403" in res.data
    assert b"Access Forbidden" in res.data


def test_unauthenticated_redirect(client):
    res = client.get('/student/dashboard')
    assert res.status_code == 302
    assert '/auth/login' in res.headers['Location']
