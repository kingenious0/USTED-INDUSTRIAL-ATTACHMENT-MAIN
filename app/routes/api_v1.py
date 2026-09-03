from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from app.models.attachment import AttachmentRecord
from app.models.activity import WeeklyActivity, DailyActivity
from app.services.attachment_service import AttachmentService

api_v1_bp = Blueprint('api_v1', __name__)


@api_v1_bp.route('/attachments/<int:attachment_id>', methods=['GET'])
@login_required
def get_attachment(attachment_id: int):
    """
    REST API endpoint for future eLogSheet / mobile client integration.
    Returns attachment metadata, status, and weekly overview.
    """
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    # Check authorization: user must be the attached student or liaison/supervisor/admin
    if current_user.is_student:
        if not current_user.student_master or attachment.student_id != current_user.student_master.id:
            abort(403)

    weeks_summary = [
        {
            'id': w.id,
            'week_number': w.week_number,
            'start_date': w.start_date.isoformat(),
            'end_date': w.end_date.isoformat(),
            'is_locked': w.is_locked,
            'locked_at': w.locked_at.isoformat() if w.locked_at else None
        }
        for w in attachment.weekly_activities
    ]

    return jsonify({
        'id': attachment.id,
        'student': {
            'index_number': attachment.student.index_number,
            'full_name': attachment.student.full_name,
            'programme': attachment.student.programme,
            'department': attachment.student.department,
            'level': attachment.student.current_level
        },
        'academic_year': attachment.academic_year,
        'duration_weeks': attachment.duration_weeks,
        'commencement_date': attachment.commencement_date.isoformat(),
        'end_date': attachment.end_date.isoformat(),
        'status': attachment.status,
        'target_organization': attachment.target_organization,
        'weeks': weeks_summary
    }), 200


@api_v1_bp.route('/attachments/<int:attachment_id>/weeks/<int:week_number>', methods=['GET'])
@login_required
def get_week_activities(attachment_id: int, week_number: int):
    """
    Returns Monday–Friday daily activities for a given attachment week.
    """
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    if current_user.is_student:
        if not current_user.student_master or attachment.student_id != current_user.student_master.id:
            abort(403)

    weekly = WeeklyActivity.query.filter_by(
        attachment_id=attachment.id,
        week_number=week_number
    ).first_or_404()

    daily_entries = [
        {
            'id': d.id,
            'day_of_week': d.day_of_week,
            'date': d.date.isoformat(),
            'start_time': d.start_time,
            'end_time': d.end_time,
            'key_tasks': d.key_tasks,
            'skills_demonstrated': d.skills_demonstrated,
            'remarks': d.remarks
        }
        for d in weekly.daily_entries
    ]

    return jsonify({
        'weekly_activity_id': weekly.id,
        'week_number': weekly.week_number,
        'start_date': weekly.start_date.isoformat(),
        'end_date': weekly.end_date.isoformat(),
        'is_locked': weekly.is_locked,
        'locked_at': weekly.locked_at.isoformat() if weekly.locked_at else None,
        'daily_activities': daily_entries
    }), 200


@api_v1_bp.route('/activities/entry/<int:entry_id>', methods=['PUT', 'POST'])
@login_required
def update_entry(entry_id: int):
    """
    Updates daily activity record via JSON REST.
    Strictly enforced: rejected if week is locked!
    """
    entry = DailyActivity.query.get_or_404(entry_id)
    weekly = entry.weekly_activity
    attachment = weekly.attachment

    if current_user.is_student:
        if not current_user.student_master or attachment.student_id != current_user.student_master.id:
            abort(403)

    data = request.get_json() or request.form
    start_time = data.get('start_time', entry.start_time)
    end_time = data.get('end_time', entry.end_time)
    key_tasks = data.get('key_tasks', entry.key_tasks)
    skills_demonstrated = data.get('skills_demonstrated', entry.skills_demonstrated)
    remarks = data.get('remarks', entry.remarks)

    try:
        updated = AttachmentService.update_daily_activity(
            daily_activity_id=entry.id,
            student_user_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            key_tasks=key_tasks,
            skills_demonstrated=skills_demonstrated,
            remarks=remarks
        )
        return jsonify({
            'message': 'Activity updated successfully',
            'id': updated.id,
            'day_of_week': updated.day_of_week
        }), 200
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_v1_bp.route('/activities/week/<int:week_id>/lock', methods=['POST'])
@login_required
def lock_week_api(week_id: int):
    """
    Student lock week endpoint via JSON REST.
    """
    weekly = WeeklyActivity.query.get_or_404(week_id)
    attachment = weekly.attachment

    if current_user.is_student:
        if not current_user.student_master or attachment.student_id != current_user.student_master.id:
            abort(403)

    try:
        locked = AttachmentService.lock_week(weekly.id, current_user.id)
        return jsonify({
            'message': f'Week {locked.week_number} successfully locked and protected as read-only.',
            'week_number': locked.week_number,
            'is_locked': locked.is_locked,
            'locked_at': locked.locked_at.isoformat()
        }), 200
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
