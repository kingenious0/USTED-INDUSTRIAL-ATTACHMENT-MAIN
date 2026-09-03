"""
app.liaison.routes - Re-exports and aliases for Liaison module routes.
Complies with PRD Section 6, 8, 41 and Project Directory Standards.
"""
from app.routes.liaison import (
    liaison_bp,
    dashboard,
    student_lookup,
    verify_and_create_attachment,
    attachments_list,
    view_attachment_detail,
    reprint_letter,
    download_letter_pdf,
    assign_supervisor,
    acceptance_queue,
    review_acceptance,
    view_scan,
)

__all__ = [
    'liaison_bp',
    'dashboard',
    'student_lookup',
    'verify_and_create_attachment',
    'attachments_list',
    'view_attachment_detail',
    'reprint_letter',
    'download_letter_pdf',
    'assign_supervisor',
    'acceptance_queue',
    'review_acceptance',
    'view_scan',
]
