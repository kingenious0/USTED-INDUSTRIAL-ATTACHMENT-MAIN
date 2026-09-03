import urllib.parse
from datetime import datetime, timezone
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.attachment import AttachmentRecord
from app.models.supervision_visit import SupervisionVisit
from app.utils.decorators import supervisor_required

supervisor_bp = Blueprint('supervisor', __name__)


def get_google_maps_nav_url(target):
    if not target:
        return None
    acc = getattr(target, 'latest_acceptance', None) or target
    lat = getattr(acc, 'latitude', None)
    lng = getattr(acc, 'longitude', None)
    if lat and lng:
        return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
    dest_str = (
        getattr(acc, 'gps_address', None)
        or getattr(acc, 'location', None)
        or getattr(acc, 'organization_name', None)
        or getattr(target, 'organization_address', None)
        or getattr(target, 'target_organization', None)
    )
    if dest_str:
        query = urllib.parse.quote(f"{dest_str}, Ghana")
        return f"https://www.google.com/maps/dir/?api=1&destination={query}"
    return None


@supervisor_bp.route('/dashboard')
@login_required
@supervisor_required
def dashboard():
    """Academic Supervisor view: list of assigned students and their placements."""
    assigned_attachments = AttachmentRecord.query.filter_by(
        academic_supervisor_id=current_user.id
    ).order_by(AttachmentRecord.created_at.desc()).all()

    # Precompute maps urls
    nav_map = {a.id: get_google_maps_nav_url(a.latest_acceptance) for a in assigned_attachments}

    return render_template(
        'supervisor/dashboard.html',
        attachments=assigned_attachments,
        nav_map=nav_map
    )


@supervisor_bp.route('/student/<int:attachment_id>')
@login_required
@supervisor_required
def view_assigned_student(attachment_id: int):
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    # Authorization check
    if not current_user.is_admin and attachment.academic_supervisor_id != current_user.id:
        abort(403)

    nav_url = get_google_maps_nav_url(attachment.latest_acceptance)
    visits = attachment.supervision_visits

    return render_template(
        'supervisor/student_detail.html',
        attachment=attachment,
        nav_url=nav_url,
        visits=visits
    )


@supervisor_bp.route('/attachment/<int:attachment_id>/log-visit', methods=['GET', 'POST'])
@login_required
@supervisor_required
def log_visit(attachment_id: int):
    """
    Field Visit Logging Route for Academic Supervisors (Pipeline 4).
    """
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    if not current_user.is_admin and attachment.academic_supervisor_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        visit_date_str = request.form.get('visit_date', '').strip()
        visit_type = request.form.get('visit_type', 'Physical In-Person').strip()
        supervisor_contacted = request.form.get('supervisor_contacted', '').strip()
        student_present = bool(request.form.get('student_present'))
        general_remarks = request.form.get('general_remarks', '').strip()
        action_items = request.form.get('action_items', '').strip()
        follow_up = bool(request.form.get('follow_up_needed'))

        try:
            visit_date = datetime.strptime(visit_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            visit_date = datetime.now(timezone.utc).date()

        visit = SupervisionVisit(
            attachment_id=attachment.id,
            lecturer_id=current_user.id,
            visit_date=visit_date,
            visit_type=visit_type,
            supervisor_contacted=supervisor_contacted or None,
            student_present=student_present,
            general_remarks=general_remarks or None,
            action_items=action_items or None,
            follow_up_needed=follow_up
        )
        db.session.add(visit)
        db.session.commit()

        flash("Supervisory field visit logged successfully.", "success")
        return redirect(url_for('supervisor.view_assigned_student', attachment_id=attachment.id))

    today_str = datetime.now().strftime('%Y-%m-%d')
    return render_template('supervisor/log_visit.html', attachment=attachment, today_str=today_str)

