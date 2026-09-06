from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, current_app, jsonify, request
from flask_login import current_user, login_required
from app.routes.auth import redirect_by_role

main_bp = Blueprint('main', __name__)


@main_bp.app_context_processor
def inject_global_vars():
    """Injects university name, current year, and settings into all Jinja templates."""
    return {
        'current_year': datetime.now().year,
        'university_name': current_app.config.get(
            'UNIVERSITY_NAME', 
            'University of Skills Training and Entrepreneurial Development (USTED)'
        ),
        'liaison_unit_name': 'Industrial Liaison Office',
        'app_version': '3.0.0'
    }


@main_bp.route('/')
def index():
    if current_user.is_authenticated and not request.args.get('landing'):
        return redirect_by_role(current_user)
    return render_template('index.html')


@main_bp.route('/portal/access/<path:index_number>')
def portal_access(index_number: str):
    """Direct root gateway for physical Introductory Letter QR codes (PRD 3.0)."""
    return redirect(url_for('auth.portal_access', index_number=index_number, token=request.args.get('token')))


@main_bp.route('/switch-role/<role>')
def switch_role(role: str):
    return redirect(url_for('auth.switch_role', role=role, next=request.args.get('next')))


@main_bp.route('/health')
def health_check():
    """System health endpoint for hosting platforms like Render."""
    return jsonify({
        'status': 'healthy',
        'system': 'USTED Industrial Attachment Management System (U-IAP)',
        'version': '3.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200


@main_bp.route('/profile', methods=['GET', 'POST'])
@main_bp.route('/account/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Unified Institutional Profile & Account Settings view accessible to all portal roles.
    Allows profile photo uploading, title/phone editing, password management,
    and read-only institutional credential governance.
    """
    import os
    import re
    from pathlib import Path
    from werkzeug.utils import secure_filename
    from flask import flash
    from app.extensions import db
    from app.models.audit import AuditAction
    from app.services.audit_service import AuditService
    from app.utils.tokens import validate_and_normalize_ghana_phone

    active_tab = request.args.get('tab', 'general')

    if request.method == 'POST':
        form_action = request.form.get('form_action', 'update_profile')

        if form_action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            office_location = request.form.get('office_location', '').strip()
            remove_avatar = request.form.get('remove_avatar') == 'true'

            if not full_name:
                flash("Formal Full Name cannot be empty.", "danger")
                return redirect(url_for('main.profile', tab='general'))

            # Validate and format Ghanaian Phone if provided
            normalized_phone = phone
            if phone:
                valid_phone, norm_p, phone_err = validate_and_normalize_ghana_phone(phone)
                if valid_phone:
                    normalized_phone = norm_p
                else:
                    # Allow cleaned alphanumeric if international / already normalized
                    cleaned_digits = re.sub(r'[^0-9+]', '', phone)
                    if len(cleaned_digits) >= 9:
                        normalized_phone = phone
                    else:
                        flash(phone_err or "Please provide a valid telephone or WhatsApp contact number.", "danger")
                        return redirect(url_for('main.profile', tab='general'))

            # Handle Avatar Removal
            upload_dir = Path(current_app.root_path) / 'static' / 'uploads' / 'avatars'
            upload_dir.mkdir(parents=True, exist_ok=True)

            if remove_avatar and current_user.avatar_path:
                old_path = upload_dir / current_user.avatar_path
                if old_path.is_file():
                    try:
                        old_path.unlink()
                    except Exception:
                        pass
                current_user.avatar_path = None

            # Handle Avatar Upload
            if 'avatar' in request.files:
                avatar_file = request.files['avatar']
                if avatar_file and avatar_file.filename:
                    ext = avatar_file.filename.rsplit('.', 1)[-1].lower()
                    if ext not in {'png', 'jpg', 'jpeg', 'webp'}:
                        flash("Unsupported image format. Please upload a PNG, JPG, or WebP headshot.", "danger")
                        return redirect(url_for('main.profile', tab='general'))

                    # Verify 2MB size limit (2 * 1024 * 1024 bytes)
                    avatar_file.seek(0, os.SEEK_END)
                    file_size = avatar_file.tell()
                    avatar_file.seek(0)
                    if file_size > 2 * 1024 * 1024:
                        flash("Profile avatar file exceeds the 2MB maximum permitted size limit.", "danger")
                        return redirect(url_for('main.profile', tab='general'))

                    # Delete previous avatar if exists
                    if current_user.avatar_path:
                        old_path = upload_dir / current_user.avatar_path
                        if old_path.is_file():
                            try:
                                old_path.unlink()
                            except Exception:
                                pass

                    new_filename = f"avatar_{current_user.id}_{int(datetime.now().timestamp())}.{ext}"
                    safe_save_path = upload_dir / new_filename
                    avatar_file.save(str(safe_save_path))
                    current_user.avatar_path = new_filename

            # Save personal particulars
            current_user.full_name = full_name
            current_user.phone = normalized_phone
            current_user.office_location = office_location

            # Synchronize phone with student master record if applicable
            if current_user.student_master and normalized_phone:
                current_user.student_master.phone = normalized_phone

            db.session.commit()

            AuditService.log(
                action=AuditAction.CONFIG_CHANGED,
                target_type='User',
                target_id=current_user.id,
                details={'action': 'PROFILE_UPDATED', 'full_name': full_name, 'phone': normalized_phone}
            )

            flash("Profile particulars and display settings updated successfully.", "success")
            return redirect(url_for('main.profile', tab='general'))

        elif form_action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not current_user.check_password(current_password):
                flash("Current password verification failed. Please try again.", "danger")
                return redirect(url_for('main.profile', tab='security'))

            if len(new_password) < 6:
                flash("New password must be at least 6 characters in length.", "danger")
                return redirect(url_for('main.profile', tab='security'))

            if new_password != confirm_password:
                flash("New passwords do not match. Please re-enter your new credentials.", "danger")
                return redirect(url_for('main.profile', tab='security'))

            current_user.set_password(new_password)
            db.session.commit()

            AuditService.log(
                action=AuditAction.CONFIG_CHANGED,
                target_type='User',
                target_id=current_user.id,
                details={'action': 'PASSWORD_CHANGED', 'username': current_user.username}
            )

            flash("Password updated successfully. Your new credentials are now active.", "success")
            return redirect(url_for('main.profile', tab='security'))

    return render_template(
        'account/profile_settings.html',
        user=current_user,
        active_tab=active_tab
    )
