from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from app.models.user import UserRole


def role_required(*allowed_roles):
    """Decorator to enforce role-based access control (RBAC)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def student_required(f):
    return role_required(UserRole.STUDENT)(f)


def liaison_required(f):
    return role_required(UserRole.LIAISON_OFFICER, UserRole.LIAISON_HEAD)(f)


def admin_required(f):
    return role_required(UserRole.LIAISON_HEAD)(f)


def supervisor_required(f):
    return role_required(UserRole.ACADEMIC_SUPERVISOR, UserRole.LIAISON_HEAD)(f)
