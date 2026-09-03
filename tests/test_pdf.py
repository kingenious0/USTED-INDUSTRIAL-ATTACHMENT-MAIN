from app.models.student_master import StudentMaster
from app.services.attachment_service import AttachmentService
from app.services.pdf_service import PDFService


def test_pdf_generation_streams(app):
    with app.app_context():
        student = StudentMaster.query.filter_by(index_number='USTED/2024/001').first()
        att = AttachmentService.create_attachment(
            student_id=student.id,
            academic_year='2025/2026',
            duration_weeks=8,
            commencement_date=student.created_at.date(),
            end_date=student.created_at.date(),
            created_by_id=1,
            target_organization='GRIDCo Kumasi Area Office'
        )

        letter, _ = AttachmentService.generate_or_reprint_letter(
            attachment_id=att.id,
            user_id=1,
            storage_service=app.storage_service,
            config=app.config
        )

        # 1. Introductory Letter PDF
        letter_pdf = PDFService.generate_introductory_letter(att, letter)
        assert letter_pdf.startswith(b"%PDF-")
        assert len(letter_pdf) > 1000

        # 2. Blank Acceptance Form PDF
        acceptance_blank_pdf = PDFService.generate_acceptance_form_template(att)
        assert acceptance_blank_pdf.startswith(b"%PDF-")
        assert len(acceptance_blank_pdf) > 1000

        # 3. Weekly Activity Sheet PDF (with Physical Supervisor Verification Box)
        week1 = att.weekly_activities[0]
        sheet_pdf = PDFService.generate_weekly_activity_sheet(week1)
        assert sheet_pdf.startswith(b"%PDF-")
        assert len(sheet_pdf) > 1000

        # 4. Multi-Week Compilation PDF
        compiled_pdf = PDFService.generate_multi_week_compilation(att)
        assert compiled_pdf.startswith(b"%PDF-")
        assert len(compiled_pdf) > 1000
