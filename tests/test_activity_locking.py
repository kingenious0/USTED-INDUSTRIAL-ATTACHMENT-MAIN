import pytest
from app.models.student_master import StudentMaster
from app.models.attachment import AttachmentRecord, AttachmentStatus
from app.models.activity import WeeklyActivity, DailyActivity
from app.services.attachment_service import AttachmentService


def _setup_active_attachment_and_get_entry(app):
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
        att.status = AttachmentStatus.LOGGING_ACTIVE
        week1 = att.weekly_activities[0]
        monday_entry = week1.daily_entries[0]
        return att.id, week1.id, monday_entry.id


def test_update_daily_activity_unlocked(client, auth, app):
    att_id, week1_id, entry_id = _setup_active_attachment_and_get_entry(app)
    auth.login('student1', 'password123')

    res = client.post(
        f'/student/activities/entry/{entry_id}/update',
        data={
            'start_time': '08:30',
            'end_time': '16:30',
            'key_tasks': 'Configured Linux server network interfaces and tested throughput.',
            'skills_demonstrated': 'TCP/IP routing, Bash scripting, Linux CLI administration.',
            'remarks': 'Supervisor approved network configuration.'
        },
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"activity entry updated successfully" in res.data

    with app.app_context():
        entry = DailyActivity.query.get(entry_id)
        assert entry.start_time == '08:30'
        assert 'Linux server network' in entry.key_tasks


def test_lock_week_and_server_side_read_only_enforcement(client, auth, app):
    """
    PRD Section 23:
    Student-controlled weekly lock.
    Once locked, the server strictly rejects any modification attempts!
    """
    att_id, week1_id, entry_id = _setup_active_attachment_and_get_entry(app)
    auth.login('student1', 'password123')

    # Student locks Week 1
    res_lock = client.post(f'/student/activities/week/{week1_id}/lock', follow_redirects=True)
    assert res_lock.status_code == 200
    assert b"Week 1 has been locked successfully" in res_lock.data

    with app.app_context():
        week = WeeklyActivity.query.get(week1_id)
        assert week.is_locked is True
        assert week.locked_at is not None

    # ATTEMPT MODIFICATION AFTER LOCK -> Server MUST REJECT!
    res_edit_attempt = client.post(
        f'/student/activities/entry/{entry_id}/update',
        data={
            'start_time': '09:00',
            'key_tasks': 'Attempting unauthorized post-lock modification'
        },
        follow_redirects=True
    )
    assert b"This week has been locked and is strictly read-only" in res_edit_attempt.data

    # Verify data did not change
    with app.app_context():
        entry = DailyActivity.query.get(entry_id)
        assert 'unauthorized post-lock' not in (entry.key_tasks or '')


def test_cross_student_unauthorized_edit_blocked(client, auth, app):
    """PRD Section 11 & 32: Student cannot access or modify another student's activities."""
    att_id, week1_id, entry_id = _setup_active_attachment_and_get_entry(app)

    # Log in as Student 2 and attempt to edit Student 1's entry
    auth.login('student2', 'password123')
    res = client.post(
        f'/student/activities/entry/{entry_id}/update',
        data={'key_tasks': 'Malicious cross-student edit attempt'},
        follow_redirects=True
    )
    # Blocked by authorization check (403 Forbidden or Permission error flash)
    assert (res.status_code == 403) or (b"Access Forbidden" in res.data) or (b"Unauthorized" in res.data)
