import secrets
import string
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.audit import AuditLog, AuditAction
from app.models.attachment import AttachmentRecord
from app.models.user import User, UserRole, AccountStatus
from app.services.audit_service import AuditService
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_temp_password(length: int = 12) -> str:
    """Generates a secure alphanumeric temporary password."""
    alphabet = string.ascii_letters + string.digits
    # Ensure at least one of each required class
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    pwd += [secrets.choice(alphabet) for _ in range(length - 3)]
    secrets.SystemRandom().shuffle(pwd)
    return ''.join(pwd)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Staff Directory
# ---------------------------------------------------------------------------

@admin_bp.route('/staff')
@login_required
@admin_required
def staff_directory():
    """Institutional staff directory with provisioning console."""
    search = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = User.query.filter(User.role != UserRole.STUDENT)

    if search:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.staff_id.ilike(f'%{search}%'),
            )
        )
    if role_filter:
        query = query.filter(User.role == role_filter)
    if status_filter:
        query = query.filter(User.account_status == status_filter)

    staff = query.order_by(User.created_at.desc()).all()

    # KPI counters
    total_staff = User.query.filter(User.role != UserRole.STUDENT).count()
    pending_claim = User.query.filter(
        User.role != UserRole.STUDENT,
        User.is_first_login == True  # noqa: E712
    ).count()
    suspended = User.query.filter(
        User.role != UserRole.STUDENT,
        User.account_status == AccountStatus.SUSPENDED
    ).count()

    return render_template(
        'admin/staff_directory.html',
        staff=staff,
        staff_roles=UserRole.STAFF_ROLES,
        role_labels=UserRole.LABELS,
        total_staff=total_staff,
        pending_claim=pending_claim,
        suspended=suspended,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        AccountStatus=AccountStatus,
    )


# ---------------------------------------------------------------------------
# Provision New Staff (AJAX POST → JSON response)
# ---------------------------------------------------------------------------

@admin_bp.route('/staff/provision', methods=['POST'])
@login_required
@admin_required
def provision_staff():
    """Creates a provisioned staff account and returns the temp password as JSON."""
    full_name   = request.form.get('full_name', '').strip()
    display_title = request.form.get('display_title', '').strip()
    email       = request.form.get('email', '').strip().lower()
    staff_id    = request.form.get('staff_id', '').strip()
    role        = request.form.get('role', '').strip()
    department  = request.form.get('department', '').strip()

    # --- Validation ---
    errors = []
    if not full_name:
        errors.append("Full name is required.")
    if not email:
        errors.append("Institutional email is required.")
    elif '@' not in email or '.' not in email.split('@')[-1]:
        errors.append("Please enter a valid email address.")
    if role not in UserRole.STAFF_ROLES:
        errors.append("Invalid role selected.")
    if User.query.filter_by(email=email).first():
        errors.append(f"An account with email '{email}' already exists.")

    if errors:
        return jsonify({'success': False, 'errors': errors}), 422

    # --- Generate temp password & create user ---
    temp_password = _generate_temp_password()
    username = staff_id or email.split('@')[0]

    # Ensure unique username
    base_username = username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1

    new_user = User(
        username=username,
        email=email,
        full_name=full_name,
        display_title=display_title or None,
        staff_id=staff_id or None,
        role=role,
        department=department or None,
        is_active=True,
        account_status=AccountStatus.PENDING_CLAIM,
        is_first_login=True,
        provisioned_by_id=current_user.id,
        provisioned_at=datetime.now(timezone.utc),
    )
    new_user.set_password(temp_password)        # main password = temp initially
    new_user.set_temp_password(temp_password)   # also stored for intercept check

    db.session.add(new_user)
    db.session.commit()

    AuditService.log(
        action=AuditAction.CONFIG_CHANGED,
        target_type='User',
        target_id=new_user.id,
        details={
            'event': 'staff_provisioned',
            'provisioned_by': current_user.username,
            'new_user': new_user.username,
            'role': role,
        }
    )

    return jsonify({
        'success': True,
        'user': {
            'id': new_user.id,
            'full_name': new_user.display_name,
            'username': new_user.username,
            'email': new_user.email,
            'role': new_user.role_label,
            'staff_id': new_user.display_staff_id,
        },
        'temp_password': temp_password,
    }), 201


# ---------------------------------------------------------------------------
# Suspend / Activate Staff
# ---------------------------------------------------------------------------

@admin_bp.route('/staff/<int:user_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_staff(user_id: int):
    """Toggles a staff account between active and suspended."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot suspend your own account.", "danger")
        return redirect(url_for('admin.staff_directory'))

    if user.account_status == AccountStatus.SUSPENDED:
        user.account_status = AccountStatus.ACTIVE
        user.is_active = True
        action_label = "reactivated"
    else:
        user.account_status = AccountStatus.SUSPENDED
        user.is_active = False
        action_label = "suspended"

    db.session.commit()
    AuditService.log(
        action=AuditAction.CONFIG_CHANGED,
        target_type='User',
        target_id=user.id,
        details={'event': f'staff_{action_label}', 'by': current_user.username}
    )
    flash(f"Account for {user.full_name} has been {action_label}.", "success")
    return redirect(url_for('admin.staff_directory'))


# ---------------------------------------------------------------------------
# Reset Staff Password (re-provision)
# ---------------------------------------------------------------------------

@admin_bp.route('/staff/<int:user_id>/reset', methods=['POST'])
@login_required
@admin_required
def reset_staff_password(user_id: int):
    """Generates a new temp password and re-flags for first-login claim."""
    user = User.query.get_or_404(user_id)

    temp_password = _generate_temp_password()
    user.set_password(temp_password)
    user.set_temp_password(temp_password)
    user.is_first_login = True
    user.account_status = AccountStatus.PENDING_CLAIM

    db.session.commit()
    AuditService.log(
        action=AuditAction.CONFIG_CHANGED,
        target_type='User',
        target_id=user.id,
        details={'event': 'staff_password_reset', 'by': current_user.username}
    )

    return jsonify({
        'success': True,
        'full_name': user.display_name,
        'username': user.username,
        'temp_password': temp_password,
    })
