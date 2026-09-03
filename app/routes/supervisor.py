from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from app.models.attachment import AttachmentRecord
from app.utils.decorators import supervisor_required

supervisor_bp = Blueprint('supervisor', __name__)


@supervisor_bp.route('/dashboard')
@login_required
@supervisor_required
def dashboard():
    """Academic Supervisor view: list of assigned students and their placements."""
    assigned_attachments = AttachmentRecord.query.filter_by(
        academic_supervisor_id=current_user.id
    ).order_by(AttachmentRecord.created_at.desc()).all()

    return render_template(
        'supervisor/dashboard.html',
        attachments=assigned_attachments
    )


@supervisor_bp.route('/student/<int:attachment_id>')
@login_required
@supervisor_required
def view_assigned_student(attachment_id: int):
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    # Authorization check
    if not current_user.is_admin and attachment.academic_supervisor_id != current_user.id:
        abort(403)

    return render_template(
        'supervisor/student_detail.html',
        attachment=attachment
    )
