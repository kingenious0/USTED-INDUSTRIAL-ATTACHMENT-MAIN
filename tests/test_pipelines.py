"""
Integration tests for the 4 U-IAP Core Operational Pipelines.
Complies with PRD Sections 6, 8, 9, 20-30, 41 and User Lifecycle Directives.
"""
import io
from app.models.student_master import StudentMaster
from app.models.attachment import AttachmentRecord, AttachmentStatus
from app.models.activity import WeeklyActivity, DailyActivity
from app.models.acceptance import AcceptanceRecord, AcceptanceStatus
from app.models.user import User


def _setup_student_attachment(client, auth, app):
    """Helper to initiate attachment for student 5230100452."""
    auth.login('liaison1', 'password123')
    with app.app_context():
        student = StudentMaster.query.filter_by(index_number="5230100452").first()
        student_id = student.id

    client.post(
        '/liaison/initiate-attachment',
        data={
            'student_id': student_id,
            'academic_year': '2025/2026',
            'duration_weeks': 8,
            'commencement_date': '2026-06-01',
            'target_organization': 'Ghana Grid Company (GRIDCo)',
            'organization_address': 'Tema Heavy Industrial Area'
        },
        follow_redirects=True
    )
    with app.app_context():
        att = AttachmentRecord.query.filter_by(student_id=student_id).order_by(AttachmentRecord.created_at.desc()).first()
        att_id = att.id
    auth.logout()
    return att_id


def test_pipeline_1_liaison_intake_and_letter_engine(client, auth, app):
    """
    PIPELINE 1: Liaison looks up student (5230100452), confirms intake,
    and initiates attachment with Introductory Letter PDF generation.
    """
    auth.login('liaison1', 'password123')

    # Step 1: Search index number
    res = client.get('/liaison/student-lookup?q=5230100452')
    assert res.status_code == 200
    assert b"5230100452" in res.data
    assert b"Elliot Paakow Entsiwah" in res.data

    with app.app_context():
        student = StudentMaster.query.filter_by(index_number="5230100452").first()
        assert student is not None
        student_id = student.id

    # Step 2: Confirmation card & initiation form
    res_get = client.get(f'/liaison/verify-student/{student_id}')
    assert res_get.status_code == 200
    assert b"Elliot Paakow Entsiwah" in res_get.data
    assert b"+ Initiate Attachment &amp; Generate Official Letter" in res_get.data or b"Initiate Attachment" in res_get.data

    # Step 3: POST /liaison/initiate-attachment
    res_post = client.post(
        '/liaison/initiate-attachment',
        data={
            'student_id': student_id,
            'academic_year': '2025/2026',
            'duration_weeks': 8,
            'commencement_date': '2026-06-01',
            'target_organization': 'Ghana Grid Company (GRIDCo)',
            'organization_address': 'Tema Heavy Industrial Area'
        },
        follow_redirects=True
    )
    assert res_post.status_code == 200
    assert b"Student physically verified" in res_post.data

    with app.app_context():
        att = AttachmentRecord.query.filter_by(student_id=student_id).order_by(AttachmentRecord.created_at.desc()).first()
        assert att is not None
        assert att.duration_weeks == 8
        assert att.is_letter_issued is True
        assert att.target_organization == 'Ghana Grid Company (GRIDCo)'
        assert len(att.introductory_letters) > 0


def test_pipeline_2_student_acceptance_and_verification(client, auth, app):
    """
    PIPELINE 2: Student uploads endorsed acceptance form scan, status transitions
    to PENDING_VERIFICATION, Liaison verifies and activates attachment to LOGGING_ACTIVE.
    """
    att_id = _setup_student_attachment(client, auth, app)

    # Student logs in
    auth.login('5230100452', 'password123')

    # Student checks dashboard
    res_dash = client.get('/student/dashboard')
    assert res_dash.status_code == 200
    assert b"Upload Completed Acceptance Form" in res_dash.data

    # Student submits completed acceptance form
    dummy_scan = b"%PDF-1.4\n%Fake stamped acceptance scan content\n%%EOF"
    res_upload = client.post(
        '/student/upload-acceptance',
        data={
            'attachment_id': att_id,
            'host_organization_name': 'Ghana Grid Company (GRIDCo)',
            'industry_location': 'Tema, Greater Accra',
            'gps_address': 'GT-012-3456',
            'sector_type': 'Statutory',
            'workplace_supervisor_name': 'Ing. Emmanuel Mensah',
            'workplace_supervisor_phone': '0244987654',
            'acceptance_scan': (io.BytesIO(dummy_scan), 'stamped_form.pdf', 'application/pdf')
        },
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert res_upload.status_code == 200
    assert b"Pending Verification" in res_upload.data

    with app.app_context():
        att = AttachmentRecord.query.get(att_id)
        assert att.is_pending_verification is True
        acceptance = att.latest_acceptance
        assert acceptance is not None
        assert acceptance.is_pending is True
        acceptance_id = acceptance.id

    # Liaison logs in to review queue
    auth.logout()
    auth.login('liaison1', 'password123')
    res_queue = client.get('/liaison/acceptance-queue')
    assert res_queue.status_code == 200
    assert b"5230100452" in res_queue.data
    assert b"Verify Acceptance &amp; Activate Attachment" in res_queue.data or b"Verify Acceptance" in res_queue.data

    # Liaison activates attachment
    res_verify = client.post(
        f'/liaison/acceptance/verify-and-activate/{acceptance_id}',
        data={'review_notes': 'Official company wet-ink stamp verified by Liaison Office.'},
        follow_redirects=True
    )
    assert res_verify.status_code == 200
    assert b"verified successfully" in res_verify.data

    with app.app_context():
        att = AttachmentRecord.query.get(att_id)
        assert att.is_logging_active is True
        assert att.can_log_activities() is True


def test_pipeline_3_elogsheet_activity_workspace_and_locking(client, auth, app):
    """
    PIPELINE 3: When logging is active, student accesses workspace, logs daily tasks,
    and locks week with server-side read-only protection.
    """
    att_id = _setup_student_attachment(client, auth, app)

    # First approve acceptance so logging becomes active
    auth.login('5230100452', 'password123')
    dummy_scan = b"%PDF-1.4\n%Fake scan\n%%EOF"
    client.post(
        '/student/upload-acceptance',
        data={
            'attachment_id': att_id,
            'host_organization_name': 'Ghana Grid Company (GRIDCo)',
            'industry_location': 'Tema, Greater Accra',
            'sector_type': 'Statutory',
            'workplace_supervisor_name': 'Ing. Emmanuel Mensah',
            'workplace_supervisor_phone': '0244987654',
            'acceptance_scan': (io.BytesIO(dummy_scan), 'scan.pdf', 'application/pdf')
        },
        content_type='multipart/form-data',
        follow_redirects=True
    )

    with app.app_context():
        att = AttachmentRecord.query.get(att_id)
        acceptance_id = att.latest_acceptance.id

    auth.logout()
    auth.login('liaison1', 'password123')
    client.post(f'/liaison/acceptance/verify-and-activate/{acceptance_id}', follow_redirects=True)

    with app.app_context():
        week_1 = WeeklyActivity.query.filter_by(attachment_id=att_id, week_number=1).first()
        monday_entry = DailyActivity.query.filter_by(weekly_activity_id=week_1.id, day_of_week='Monday').first()
        entry_id = monday_entry.id
        week_id = week_1.id

    auth.logout()
    auth.login('5230100452', 'password123')

    # Student dashboard now displays active banner
    res_dash = client.get('/student/dashboard')
    assert res_dash.status_code == 200
    assert b"Attachment Active: Ghana Grid Company (GRIDCo)" in res_dash.data
    assert b"Open Weekly Activity Workspace" in res_dash.data

    # Open workspace
    res_work = client.get(f'/activities/workspace/{att_id}')
    assert res_work.status_code == 200
    assert b"All Weekdays" in res_work.data
    assert b"Weekday Jump" in res_work.data

    # Save Monday entry
    res_save = client.post(
        f'/student/activities/entry/{entry_id}/update',
        data={
            'start_time': '08:30',
            'end_time': '16:45',
            'key_tasks': 'Inspection of 161kV substation switchgear and busbars.',
            'skills_demonstrated': 'High voltage safety protocol adherence and single-line diagram analysis.',
            'remarks': 'Mentored by Senior Protection Engineer.'
        },
        follow_redirects=True
    )
    assert res_save.status_code == 200
    assert b"Monday activity entry updated successfully" in res_save.data

    # Lock Week 1
    res_lock = client.post(
        f'/student/attachment/week/{week_id}/lock',
        follow_redirects=True
    )
    assert res_lock.status_code == 200
    assert b"has been locked successfully" in res_lock.data
    with app.app_context():
        w1 = WeeklyActivity.query.get(week_id)
        assert w1.is_locked is True

    # Subsequent edit attempts are blocked by server-side lock enforcement
    res_blocked = client.post(
        f'/student/activities/entry/{entry_id}/update',
        data={'key_tasks': 'Tampering with locked logbook attempt'},
        follow_redirects=True
    )
    assert b"Permission denied" in res_blocked.data or b"read-only" in res_blocked.data or b"Locked" in res_blocked.data


def test_pipeline_4_weekly_verification_pdf_generation(client, auth, app):
    """
    PIPELINE 4: Weekly verification sheet PDF generation in Landscape A4 with physical
    verification container, supervisor comment lines, and wet-ink stamp box.
    """
    att_id = _setup_student_attachment(client, auth, app)
    with app.app_context():
        week_1 = WeeklyActivity.query.filter_by(attachment_id=att_id, week_number=1).first()
        week_id = week_1.id

    auth.login('5230100452', 'password123')
    res_pdf = client.get(f'/student/attachment/week/{week_id}/download-sheet')
    assert res_pdf.status_code == 200
    assert res_pdf.mimetype == 'application/pdf'
    assert len(res_pdf.data) > 1000
