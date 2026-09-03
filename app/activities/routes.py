"""
app.activities.routes - Direct routing for eLogSheet Workspace.
Complies with PRD Section 9, 25-30 and Project Directory Standards.
"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.activities import activities_bp
from app.utils.decorators import student_required
from app.models.attachment import AttachmentRecord
from app.models.activity import WeeklyActivity
from app.routes.student import activities, update_daily_entry, lock_week, download_weekly_sheet


@activities_bp.route('/workspace')
@activities_bp.route('/workspace/<int:attachment_id>')
@login_required
@student_required
def workspace(attachment_id: int = None):
    """
    Renders eLogSheet workspace for active attachment.
    """
    if not attachment_id:
        if current_user.student_master and current_user.student_master.attachments.count() > 0:
            att = current_user.student_master.attachments.order_by(AttachmentRecord.created_at.desc()).first()
            if att:
                attachment_id = att.id
            else:
                flash('No active attachment found.', 'warning')
                return redirect(url_for('student.dashboard'))
        else:
            flash('No student record or attachment found.', 'warning')
            return redirect(url_for('student.dashboard'))

    return activities(attachment_id)


__all__ = [
    'workspace',
    'activities',
    'update_daily_entry',
    'lock_week',
    'download_weekly_sheet',
]
