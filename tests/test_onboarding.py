import pytest
from app.extensions import db
from app.models.user import User, UserRole
from app.models.student_master import StudentMaster
from app.models.attachment import AttachmentRecord, AttachmentStatus
from app.utils.tokens import generate_qr_token, decode_qr_onboard_token
from datetime import date, timedelta


def test_qr_token_generation_and_decoding(app):
    """Test cryptographic token creation, payload extraction, and tampering detection."""
    secret = app.config['SECRET_KEY']
    index_num = "USTED/2024/003"

    token = generate_qr_token(index_num, secret, attachment_id=42)
    assert token is not None
    assert len(token) > 20

    # Test valid decoding
    is_valid, data, err = decode_qr_onboard_token(token, secret, max_age=3600)
    assert is_valid is True
    assert err is None
    assert data['index_number'] == index_num
    assert data['attachment_id'] == 42

    # Test tampered token
    tampered = token[:-4] + "abcd"
    is_valid, data, err = decode_qr_onboard_token(tampered, secret)
    assert is_valid is False
    assert err is not None

    # Test expired token
    is_valid, data, err = decode_qr_onboard_token(token, secret, max_age=-1)
    assert is_valid is False
    assert "expired" in err.lower()


def test_onboard_get_unregistered_student(client, app):
    """GET /student/onboard/<token> displays prefilled student info."""
    secret = app.config['SECRET_KEY']
    index_num = "USTED/2024/003"  # Kwame Antwi-Boasiako (has no user account)

    token = generate_qr_token(index_num, secret)
    resp = client.get(f'/student/onboard/{token}')

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Kwame Antwi-Boasiako" in html
    assert index_num in html
    assert "BSc. Mechanical Technology Education" in html
    assert "Activate Account" in html


def test_onboard_get_invalid_token(client):
    """GET /student/onboard/<invalid_token> redirects to login with flash warning."""
    resp = client.get('/student/onboard/completely-invalid-token', follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Invalid or altered" in html or "invalid or has expired" in html


def test_onboard_get_already_registered_student(client, app):
    """GET /student/onboard/<token> for already registered student redirects to login."""
    secret = app.config['SECRET_KEY']
    index_num = "USTED/2024/001"  # Kofi Mensah Boateng (already seeded as student1)

    token = generate_qr_token(index_num, secret)
    resp = client.get(f'/student/onboard/{token}', follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "already been created" in html


def test_onboard_post_password_mismatch(client, app):
    """POST /student/onboard/<token> rejects mismatched passwords."""
    secret = app.config['SECRET_KEY']
    index_num = "USTED/2024/004"  # Esi Mansa Danquah

    token = generate_qr_token(index_num, secret)
    resp = client.post(
        f'/student/onboard/{token}',
        data={
            'phone': '0555890123',
            'password': 'Password123!',
            'confirm_password': 'DifferentPassword456!'
        },
        follow_redirects=True
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Passwords do not match" in html


def test_onboard_post_short_password(client, app):
    """POST /student/onboard/<token> rejects passwords under 8 characters."""
    secret = app.config['SECRET_KEY']
    index_num = "USTED/2024/004"

    token = generate_qr_token(index_num, secret)
    resp = client.post(
        f'/student/onboard/{token}',
        data={
            'phone': '0555890123',
            'password': 'short',
            'confirm_password': 'short'
        },
        follow_redirects=True
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "at least 8 characters" in html


def test_onboard_post_successful_account_creation(client, app):
    """POST /student/onboard/<token> successfully creates user and logs in."""
    secret = app.config['SECRET_KEY']
    index_num = "USTED/2024/005"  # Emmanuel Yaw Frimpong

    with app.app_context():
        student = StudentMaster.query.filter_by(index_number=index_num).first()
        assert student is not None
        # Verify no user exists yet
        assert User.query.filter_by(username=index_num).first() is None

    token = generate_qr_token(index_num, secret)
    resp = client.post(
        f'/student/onboard/{token}',
        data={
            'phone': '0243567890',
            'password': 'SecurePassword2026!',
            'confirm_password': 'SecurePassword2026!'
        },
        follow_redirects=True
    )

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Account created successfully" in html
    assert "Emmanuel Yaw Frimpong" in html

    # Verify user created in database with proper role and hashed password
    with app.app_context():
        new_user = User.query.filter_by(username=index_num).first()
        assert new_user is not None
        assert new_user.role == UserRole.STUDENT
        assert new_user.check_password('SecurePassword2026!') is True
        assert new_user.student_master_id == student.id


def test_elogsheet_sso_launch(client, app):
    """GET /student/attachment/<id>/launch-elogsheet generates SSO JWT and redirects externally."""
    with app.app_context():
        student = StudentMaster.query.filter_by(index_number="USTED/2024/001").first()
        user = User.query.filter_by(username="student1").first()

        # Create active attachment for Kofi
        att = AttachmentRecord(
            student_id=student.id,
            academic_year="2025/2026",
            duration_weeks=8,
            commencement_date=date(2026, 6, 1),
            end_date=date(2026, 7, 24),
            created_by_id=user.id,
            status=AttachmentStatus.ACCEPTANCE_APPROVED
        )
        db.session.add(att)
        db.session.commit()
        att_id = att.id

    # Login as student1
    client.post('/auth/login', data={'username': 'student1', 'password': 'password123'})

    # Request launch-elogsheet
    resp = client.get(f'/student/attachment/{att_id}/launch-elogsheet')
    assert resp.status_code == 302
    redirect_location = resp.headers['Location']
    assert "sso_token=" in redirect_location
