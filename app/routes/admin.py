from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.models.audit import AuditLog, AuditAction
from app.models.attachment import AttachmentRecord
from app.models.user import User
from app.services.audit_service import AuditService
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_attachments = AttachmentRecord.query.count()
    total_audits = AuditLog.query.count()
    recent_audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_attachments=total_attachments,
        total_audits=total_audits,
        recent_audits=recent_audits
    )


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """Audit trail inspection complying with PRD Section 31."""
    action_filter  = request.args.get('action', '').strip()
    actor_filter   = request.args.get('actor', '').strip()
    role_filter    = request.args.get('role', '').strip()
    page           = request.args.get('page', 1, type=int)
    per_page       = request.args.get('per_page', 20, type=int)
    if per_page not in (20, 50, 100):
        per_page = 20

    query = AuditLog.query

    if action_filter:
        query = query.filter_by(action=action_filter)
    if role_filter:
        query = query.filter(AuditLog.actor_role == role_filter)
    if actor_filter:
        query = query.filter(AuditLog.actor_username.ilike(f'%{actor_filter}%'))

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    actions = [
        AuditAction.USER_LOGIN,
        AuditAction.ATTACHMENT_INITIATED,
        AuditAction.LETTER_GENERATED,
        AuditAction.LETTER_REPRINTED,
        AuditAction.ACCEPTANCE_UPLOADED,
        AuditAction.ACCEPTANCE_REVIEWED,
        AuditAction.WEEK_LOCKED,
        AuditAction.ACTIVITY_UPDATED,
        AuditAction.CONFIG_CHANGED
    ]

    return render_template(
        'admin/audit_logs.html',
        logs=pagination.items,
        pagination=pagination,
        actions=actions,
        selected_action=action_filter,
        actor_filter=actor_filter,
        role_filter=role_filter,
        per_page=per_page,
    )


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """System configuration & Institutional Policy Toggles (PRD Section 19 & OQ-04)."""
    if request.method == 'POST':
        require_approval = bool(request.form.get('require_acceptance_approval'))
        current_app.config['REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING'] = require_approval

        AuditService.log(
            action=AuditAction.CONFIG_CHANGED,
            target_type='SystemConfig',
            details={'REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING': require_approval}
        )

        flash('System operational policy updated successfully.', 'success')
        return redirect(url_for('admin.settings'))

    current_setting = current_app.config.get('REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING', False)
    return render_template('admin/settings.html', require_approval=current_setting)
