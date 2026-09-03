"""
app.students.routes - Re-exports and aliases for Student module routes.
Complies with PRD Section 8, 20-24 and Project Directory Standards.
"""
from app.routes.student import (
    student_bp,
    dashboard,
    view_attachment,
    download_letter,
    download_blank_acceptance_form,
    upload_acceptance,
    view_uploaded_scan,
    activities,
    update_daily_entry,
    lock_week,
    download_weekly_sheet,
    download_compiled_report,
)

__all__ = [
    'student_bp',
    'dashboard',
    'view_attachment',
    'download_letter',
    'download_blank_acceptance_form',
    'upload_acceptance',
    'view_uploaded_scan',
    'activities',
    'update_daily_entry',
    'lock_week',
    'download_weekly_sheet',
    'download_compiled_report',
]
