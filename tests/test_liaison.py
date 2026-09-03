from app.models.attachment import AttachmentRecord, AttachmentStatus
from app.models.student_master import StudentMaster


def test_student_lookup(client, auth):
    auth.login('liaison1', 'password123')
    # Lookup by index number
    res = client.get('/liaison/students/lookup?q=USTED/2024/001')
    assert res.status_code == 200
    assert b"Kofi Mensah Boateng" in res.data
    assert b"Information Technology Education" in res.data
    assert b"Level 300" in res.data

    # Lookup non-existent index number (PRD Section 43)
    res_none = client.get('/liaison/students/lookup?q=NONEXISTENT/999')
    assert res_none.status_code == 200
    assert b"No Student Found" in res_none.data


def test_verify_and_create_attachment(client, auth, app):
    auth.login('liaison1', 'password123')
    student = StudentMaster.query.filter_by(index_number='USTED/2024/001').first()

    # Post physical verification intake form
    res = client.post(
        f'/liaison/verify-and-create/{student.id}',
        data={
            'academic_year': '2025/2026',
            'duration_weeks': '8',
            'commencement_date': '2026-06-01',
            'target_organization': 'Ghana Grid Company Ltd (GRIDCo)',
            'organization_address': 'Kumasi'
        },
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"Student physically verified" in res.data

    with app.app_context():
        att = AttachmentRecord.query.filter_by(student_id=student.id).first()
        assert att is not None
        assert att.duration_weeks == 8
        assert att.academic_year == '2025/2026'
        assert att.target_organization == 'Ghana Grid Company Ltd (GRIDCo)'
        # Introductory letter automatically generated
        assert att.letters is not None
        assert len(att.letters) == 1
        assert att.letters[0].reference_number.startswith('USTED/ILU/2025-2026/')
        # 8 weeks provisioned with 5 days each
        assert len(att.weekly_activities) == 8
        assert len(att.weekly_activities[0].daily_entries) == 5
