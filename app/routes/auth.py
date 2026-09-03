from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User, UserRole
from app.models.audit import AuditAction
from app.services.audit_service import AuditService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_by_role(current_user)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact the Industrial Liaison Unit.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            AuditService.log(
                action=AuditAction.USER_LOGIN,
                target_type='User',
                target_id=user.id,
                details={'username': user.username, 'role': user.role}
            )

            flash(f'Welcome, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect_by_role(user)

        flash('Invalid username or password. Please try again.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    AuditService.log(
        action=AuditAction.USER_LOGOUT,
        target_type='User',
        target_id=current_user.id,
        details={'username': current_user.username}
    )
    logout_user()
    flash('You have been safely logged out.', 'info')
    return redirect(url_for('auth.login'))


def redirect_by_role(user: User):
    """Redirects authenticated users to their designated role dashboard."""
    if user.role == UserRole.STUDENT:
        return redirect(url_for('student.dashboard'))
    elif user.role in (UserRole.LIAISON_OFFICER, UserRole.LIAISON_HEAD):
        return redirect(url_for('liaison.dashboard'))
    elif user.role == UserRole.ACADEMIC_SUPERVISOR:
        return redirect(url_for('supervisor.dashboard'))
    return redirect(url_for('main.index'))
