import io
import time
import jwt
import pytest
from datetime import datetime, date

from app.models.user import User, UserRole
from app.models.student_master import StudentMaster
from app.models.attachment import AttachmentRecord, AttachmentStatus
from app.models.acceptance import AcceptanceRecord, AcceptanceStatus
from app.models.supervision_visit import SupervisionVisit
from app.services.attachment_service import AttachmentService
from app.utils.tokens import (
    validate_and_normalize_ghana_phone,
    generate_qr_token,
    verify_qr_token,
    generate_elogbook_sso_jwt,
)
from app.services.pdf_service import PDFService
from app.routes.supervisor import get_google_maps_nav_url


def _get_or_create_attachment(app, index_number='USTED/2024/001'):
    with app.app_context():
        student = StudentMaster.query.filter_by(index_number=index_number).first()
        att = student.attachments.first()
        if not att:
            att = AttachmentService.create_attachment(
                student_id=student.id,
                academic_year='2025/2026',
                duration_weeks=8,
                commencement_date=student.created_at.date(),
                end_date=student.created_at.date(),
                created_by_id=1,
                target_organization='GRIDCo'
            )
        return att.id


def test_pipeline_1_walk_in_desk_quick_registration(client, auth, app):
    """
    Pipeline 1 (Walk-In): Liaison Officer registers student at service desk,
    instantly creates attachment record, and generates Introductory Letter with embedded QR.
    """
    auth.login('liaison1', 'password123')

    # Quick register walk-in student
    res = client.post(
        '/liaison/students/quick-register',
        data={
            'index_number': '5230999001',
            'full_name': 'KWABENA AFRIYIE OWUSU',
            'programme': 'B.Sc. Mechanical Engineering',
            'department': 'Department of Mechanical Engineering',
            'current_level': '300',
            'phone': '0244123456',
            'academic_year': '2025/2026',
            'duration_weeks': '8',
            'commencement_date': '2026-06-01',
            'target_organization': 'Newmont Ghana Gold Ltd',
            'organization_address': 'Ahafo Mine, Kenyasi'
        },
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"KWABENA AFRIYIE OWUSU" in res.data
    assert b"registered successfully" in res.data

    with app.app_context():
        student = StudentMaster.query.filter_by(index_number='5230999001').first()
        assert student is not None
        assert student.programme == 'B.Sc. Mechanical Engineering'
        assert student.phone == '+233244123456'

        att = AttachmentRecord.query.filter_by(student_id=student.id).first()
        assert att is not None
        assert att.target_organization == 'Newmont Ghana Gold Ltd'
        assert att.duration_weeks == 8

        # Check Introductory Letter was automatically generated
        assert len(att.letters) == 1
        letter = att.letters[0]
        assert letter.reference_number is not None


def test_pipeline_2_qr_gateway_and_activation(client, app):
    """
    Pipeline 2 (QR Gateway & Activation):
    Generates 24-hr secure QR onboarding token, verifies entrypoint and student self-activation
    for an unactivated student, as well as seamless login for an existing user.
    """
    with app.app_context():
        secret_key = app.config['SECRET_KEY']
        token_unactivated = generate_qr_token('USTED/2024/003', secret_key)
        is_valid, _ = verify_qr_token(token_unactivated, 'USTED/2024/003', secret_key, max_age=86400)
        assert is_valid is True
        # Verify expired token rejected
        is_valid_exp, _ = verify_qr_token(token_unactivated, 'USTED/2024/003', secret_key, max_age=-1)
        assert is_valid_exp is False

    # 1. Unactivated student scans QR link -> Redirects to Activation page
    res_access = client.get(f'/portal/access/USTED/2024/003?token={token_unactivated}', follow_redirects=True)
    assert res_access.status_code == 200
    assert b"Activate Student Portal" in res_access.data
    assert b"USTED/2024/003" in res_access.data

    # Complete activation with valid Ghanaian mobile number and password
    res_activate = client.post(
        '/auth/activate',
        data={
            'index_number': 'USTED/2024/003',
            'token': token_unactivated,
            'phone': '0551234567',
            'password': 'NewSecurePassword123!',
            'confirm_password': 'NewSecurePassword123!'
        },
        follow_redirects=True
    )
    assert res_activate.status_code == 200
    assert b"Account activated successfully" in res_activate.data

    with app.app_context():
        user = User.query.filter_by(username='USTED/2024/003').first()
        assert user is not None
        assert user.is_active is True
        assert user.check_password('NewSecurePassword123!') is True

        student = StudentMaster.query.filter_by(index_number='USTED/2024/003').first()
        assert student.phone == '+233551234567'

    # 2. Already-activated student scans QR link -> Instant login
    with app.app_context():
        token_existing = generate_qr_token('5230100452', secret_key)
    res_existing = client.get(f'/portal/access/5230100452?token={token_existing}', follow_redirects=True)
    assert res_existing.status_code == 200
    assert b"Verified via 24-Hour QR Gateway" in res_existing.data


def test_pipeline_2_phone_validation_regex():
    """
    Pipeline 2: Validate Ghanaian mobile numbers across MTN, Telecel, and AT networks.
    """
    # Valid formats
    valid, norm, err = validate_and_normalize_ghana_phone('0244123456')
    assert valid is True and norm == '+233244123456'

    valid, norm, err = validate_and_normalize_ghana_phone('+233 20 123 4567')
    assert valid is True and norm == '+233201234567'

    valid, norm, err = validate_and_normalize_ghana_phone('233551234567')
    assert valid is True and norm == '+233551234567'

    valid, norm, err = validate_and_normalize_ghana_phone('0271234567')
    assert valid is True and norm == '+233271234567'

    # Invalid formats
    valid, norm, err = validate_and_normalize_ghana_phone('0123456789')
    assert valid is False and norm is None

    valid, norm, err = validate_and_normalize_ghana_phone('12345')
    assert valid is False and norm is None

    valid, norm, err = validate_and_normalize_ghana_phone('+15551234567')
    assert valid is False and norm is None

    valid, norm, err = validate_and_normalize_ghana_phone('')
    assert valid is False and norm is None


def test_pipeline_3_acceptance_geolocation_capture(client, auth, app):
    """
    Pipeline 3: Student uploads acceptance with Ghana Post GPS, Landmark, and exact GIS coordinates.
    """
    att_id = _get_or_create_attachment(app, 'USTED/2024/001')
    auth.login('student1', 'password123')

    dummy_scan = b"%PDF-1.4\n%Fake acceptance scan with wet stamp\n%%EOF"
    res = client.post(
        f'/student/attachment/{att_id}/acceptance/upload',
        data={
            'company_name': 'Vodafone Ghana (Telecel)',
            'industry_sector': 'Telecommunications & Networks',
            'phone': '0201234567',
            'email': 'hr@telecel.com.gh',
            'region': 'Ashanti Region',
            'district_town': 'Asokwa, Kumasi',
            'gps_address': 'AK-039-2345',
            'landmark': 'Opposite Ahodwo Roundabout Total Energies',
            'latitude': '6.674512',
            'longitude': '-1.571420',
            'supervisor_name': 'Ing. Kwame Poku',
            'supervisor_phone': '0209876543',
            'acceptance_scan': (io.BytesIO(dummy_scan), 'acceptance_scan.pdf', 'application/pdf')
        },
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert res.status_code == 200

    with app.app_context():
        acceptance = AcceptanceRecord.query.filter_by(attachment_id=att_id).first()
        assert acceptance is not None
        assert acceptance.region == 'Ashanti Region'
        assert acceptance.district_town == 'Asokwa, Kumasi'
        assert acceptance.gps_address == 'AK-039-2345'
        assert acceptance.landmark == 'Opposite Ahodwo Roundabout Total Energies'
        assert pytest.approx(acceptance.latitude, 0.0001) == 6.674512
        assert pytest.approx(acceptance.longitude, 0.0001) == -1.571420


def test_pipeline_4_zonal_mapping_and_supervisor_allocation(client, auth, app):
    """
    Pipeline 4: Liaison views regional clusters and batch assigns academic supervisor.
    Supervisor logs field visit and accesses Google Maps navigation link.
    """
    att_id = _get_or_create_attachment(app, 'USTED/2024/001')
    auth.login('liaison1', 'password123')

    # View Zonal Mapping Hub
    res_hub = client.get('/liaison/supervision/zonal-mapping')
    assert res_hub.status_code == 200
    assert b"Zonal Mapping" in res_hub.data
    assert b"Supervisor Allocation" in res_hub.data

    with app.app_context():
        supervisor = User.query.filter_by(role=UserRole.ACADEMIC_SUPERVISOR).first()
        sup_id = supervisor.id

    # Batch allocate attachment to academic supervisor
    res_alloc = client.post(
        '/liaison/supervision/zonal-mapping',
        data={
            'supervisor_id': sup_id,
            'attachment_ids': [att_id]
        },
        follow_redirects=True
    )
    assert res_alloc.status_code == 200
    assert b"Successfully allocated" in res_alloc.data

    with app.app_context():
        updated_att = AttachmentRecord.query.get(att_id)
        assert updated_att.academic_supervisor_id == sup_id

    # Verify Google Maps link generation
    with app.app_context():
        updated_att = AttachmentRecord.query.get(att_id)
        nav_url = get_google_maps_nav_url(updated_att)
        assert nav_url is not None
        assert "google.com/maps/dir" in nav_url

    # Supervisor logs field visit
    auth.logout()
    auth.login('supervisor1', 'password123')

    res_log = client.post(
        f'/supervisor/attachment/{att_id}/log-visit',
        data={
            'visit_date': '2026-06-15',
            'visit_type': 'in_person',
            'student_present': '1',
            'supervisor_contacted': '1',
            'general_remarks': 'Student demonstrated excellent proficiency in network rack cabling.',
            'action_items': 'Ensure weekly sheets are signed every Friday afternoon.',
            'follow_up_needed': '0'
        },
        follow_redirects=True
    )
    assert res_log.status_code == 200
    assert b"Supervisory field visit logged successfully" in res_log.data

    with app.app_context():
        visit = SupervisionVisit.query.filter_by(attachment_id=att_id).first()
        assert visit is not None
        assert visit.student_present is True
        assert bool(visit.supervisor_contacted) is True
        assert "network rack cabling" in visit.general_remarks


def test_pipeline_5_decoupled_elogbook_sso(client, auth, app):
    """
    Pipeline 5: 120-second cryptographically signed JWT generation and SSO launch redirect.
    """
    att_id = _get_or_create_attachment(app, 'USTED/2024/001')
    auth.login('student1', 'password123')

    with app.app_context():
        student = StudentMaster.query.filter_by(index_number='USTED/2024/001').first()
        att = AttachmentRecord.query.get(att_id)
        secret_key = app.config['SECRET_KEY']

        # Unit test JWT generation
        token = generate_elogbook_sso_jwt(student, att, secret_key, expires_in=120)
        decoded = jwt.decode(token, secret_key, algorithms=['HS256'])
        assert decoded['iss'] == 'usted-u-iap-portal'
        assert decoded['sub'] == student.index_number
        assert decoded['full_name'] == student.full_name
        assert decoded['duration_weeks'] == att.duration_weeks
        assert decoded['exp'] > time.time()

    # Route test SSO launch redirect
    res_launch = client.get(f'/student/attachment/{att_id}/launch-elogsheet')
    assert res_launch.status_code == 302
    redirect_location = res_launch.headers['Location']
    assert "sso_token=" in redirect_location
    assert "usted-elogbook.vercel.app" in redirect_location


def test_pipeline_6_confidential_assessment_and_blank_templates(client, auth, app):
    """
    Pipeline 6: Generation of 2-Page Confidential 20-Item Assessment Form PDF
    and generic blank document templates.
    """
    att_id = _get_or_create_attachment(app, 'USTED/2024/001')
    auth.login('student1', 'password123')

    # 1. Download populated Confidential Assessment Form
    res_ass = client.get(f'/student/attachment/{att_id}/assessment-form/download')
    assert res_ass.status_code == 200
    assert res_ass.mimetype == 'application/pdf'
    assert len(res_ass.data) > 3000
    assert b'%PDF' in res_ass.data[:10]

    # 2. Download generic Blank Acceptance Form
    res_blank_acc = client.get('/student/documents/blank-acceptance-form')
    assert res_blank_acc.status_code == 200
    assert res_blank_acc.mimetype == 'application/pdf'
    assert len(res_blank_acc.data) > 3000

    # 3. Download generic Blank Assessment Form
    res_blank_ass = client.get('/student/documents/blank-assessment-form')
    assert res_blank_ass.status_code == 200
    assert res_blank_ass.mimetype == 'application/pdf'
    assert len(res_blank_ass.data) > 3000
