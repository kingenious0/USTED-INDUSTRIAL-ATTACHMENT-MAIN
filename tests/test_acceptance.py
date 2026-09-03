import io
from app.models.student_master import StudentMaster
from app.models.attachment import AttachmentRecord
from app.models.acceptance import AcceptanceRecord, AcceptanceStatus
from app.services.attachment_service import AttachmentService


def _setup_active_attachment(app):
    with app.app_context():
        student = StudentMaster.query.filter_by(index_number='USTED/2024/001').first()
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


def test_upload_acceptance_valid(client, auth, app):
    att_id = _setup_active_attachment(app)
    auth.login('student1', 'password123')

    dummy_pdf = b"%PDF-1.4 dummy acceptance form scan content"
    res = client.post(
        f'/student/attachment/{att_id}/acceptance/upload',
        data={
            'organization_name': 'GRIDCo Kumasi Area Office',
            'organization_type': 'Energy / Utility',
            'location': 'Adum, Kumasi',
            'postal_address': 'P.O. Box 100, Kumasi',
            'telephone': '0322099999',
            'email': 'gridco@gridcogh.com',
            'workplace_supervisor_name': 'Ing. Kwame Mensah',
            'workplace_supervisor_phone': '0244111222',
            'acceptance_scan': (io.BytesIO(dummy_pdf), 'endorsed_acceptance.pdf', 'application/pdf')
        },
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"Acceptance Form uploaded successfully" in res.data

    with app.app_context():
        acceptance = AcceptanceRecord.query.filter_by(attachment_id=att_id).first()
        assert acceptance is not None
        assert acceptance.status == AcceptanceStatus.PENDING_REVIEW
        assert acceptance.organization_name == 'GRIDCo Kumasi Area Office'


def test_upload_acceptance_invalid_file_extension(client, auth, app):
    att_id = _setup_active_attachment(app)
    auth.login('student1', 'password123')

    dummy_exe = b"fake executable binary"
    res = client.post(
        f'/student/attachment/{att_id}/acceptance/upload',
        data={
            'organization_name': 'GRIDCo Kumasi Area Office',
            'location': 'Adum, Kumasi',
            'telephone': '0322099999',
            'acceptance_scan': (io.BytesIO(dummy_exe), 'dangerous.exe', 'application/x-msdownload')
        },
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"is not permitted" in res.data


def test_liaison_review_acceptance(client, auth, app):
    att_id = _setup_active_attachment(app)
    auth.login('student1', 'password123')

    # Upload
    dummy_pdf = b"%PDF-1.4 dummy scan"
    client.post(
        f'/student/attachment/{att_id}/acceptance/upload',
        data={
            'organization_name': 'GRIDCo',
            'location': 'Kumasi',
            'telephone': '0322099999',
            'acceptance_scan': (io.BytesIO(dummy_pdf), 'scan.pdf', 'application/pdf')
        },
        content_type='multipart/form-data',
        follow_redirects=True
    )
    auth.logout()

    # Liaison Reviews
    auth.login('liaison1', 'password123')
    with app.app_context():
        acc = AcceptanceRecord.query.filter_by(attachment_id=att_id).first()
        acc_id = acc.id

    # Attempt approve WITHOUT wet-ink stamp / signature -> Blocked!
    res_blocked = client.post(
        f'/liaison/acceptance/review/{acc_id}',
        data={'decision': 'approve'},
        follow_redirects=True
    )
    assert b"Cannot approve" in res_blocked.data

    # Approve with verified stamp and signature
    res_approved = client.post(
        f'/liaison/acceptance/review/{acc_id}',
        data={
            'decision': 'approve',
            'has_supervisor_signature': '1',
            'has_official_stamp': '1',
            'review_notes': 'Official wet-ink stamp and supervisor signature confirmed.'
        },
        follow_redirects=True
    )
    assert res_approved.status_code == 200
    assert b"reviewed with status: APPROVED" in res_approved.data
