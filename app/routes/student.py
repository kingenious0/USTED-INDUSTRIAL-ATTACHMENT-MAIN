from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
    send_file, current_app, Response
)
from flask_login import login_required, current_user
import io
from app.extensions import db
from app.models.attachment import AttachmentRecord, AttachmentStatus
from app.models.activity import WeeklyActivity, DailyActivity
from app.models.acceptance import AcceptanceRecord
from app.services.attachment_service import AttachmentService
from app.services.pdf_service import PDFService
from app.utils.decorators import student_required
from app.utils.tokens import generate_elogbook_sso_jwt

student_bp = Blueprint('student', __name__)


def _get_student_attachment_or_404(attachment_id: int) -> AttachmentRecord:
    """Helper ensuring students can only access their own attachment record."""
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    if not current_user.student_master or attachment.student_id != current_user.student_master.id:
        abort(403)
    return attachment


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    student_master = current_user.student_master
    if not student_master:
        flash("Your user profile is not linked to a university student master record. Please visit the Industrial Liaison Unit.", "warning")
        return render_template('student/dashboard.html', student=None, attachments=[])

    attachments = AttachmentRecord.query.filter_by(student_id=student_master.id).order_by(AttachmentRecord.created_at.desc()).all()
    active_attachment = attachments[0] if attachments else None

    require_approval = current_app.config.get('REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING', False)
    can_log = active_attachment.can_log_activities(require_approval) if active_attachment else False

    return render_template(
        'student/dashboard.html',
        student=student_master,
        attachments=attachments,
        active_attachment=active_attachment,
        can_log=can_log
    )


@student_bp.route('/attachment/<int:attachment_id>')
@login_required
@student_required
def view_attachment(attachment_id: int):
    attachment = _get_student_attachment_or_404(attachment_id)
    require_approval = current_app.config.get('REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING', False)
    can_log = attachment.can_log_activities(require_approval)

    return render_template(
        'student/view_attachment.html',
        attachment=attachment,
        can_log=can_log
    )


@student_bp.route('/attachment/<int:attachment_id>/letter/download')
@login_required
@student_required
def download_letter(attachment_id: int):
    attachment = _get_student_attachment_or_404(attachment_id)
    letter = attachment.latest_letter
    if not letter:
        flash("An official Introductory Letter has not been generated for this attachment yet. Please contact the Liaison Office.", "warning")
        return redirect(url_for('student.view_attachment', attachment_id=attachment.id))

    file_bytes = current_app.storage_service.retrieve(letter.storage_key)
    if not file_bytes:
        # Regenerate if file missing from local storage
        _, file_bytes = AttachmentService.generate_or_reprint_letter(
            attachment.id,
            current_user.id,
            current_app.storage_service,
            config=current_app.config
        )

    return send_file(
        io.BytesIO(file_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Introductory_Letter_{attachment.student.index_number.replace('/', '_')}.pdf"
    )


@student_bp.route('/attachment/<int:attachment_id>/acceptance/blank-form')
@login_required
@student_required
def download_blank_acceptance_form(attachment_id: int):
    """Generates and downloads the standard physical WEL Acceptance Form."""
    attachment = _get_student_attachment_or_404(attachment_id)
    pdf_bytes = PDFService.generate_acceptance_form_template(attachment)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"WEL_Acceptance_Form_{attachment.student.index_number.replace('/', '_')}.pdf"
    )


@student_bp.route('/upload-acceptance', methods=['POST'])
@student_bp.route('/upload-acceptance/<int:attachment_id>', methods=['GET', 'POST'])
@student_bp.route('/attachment/<int:attachment_id>/acceptance/upload', methods=['GET', 'POST'])
@login_required
@student_required
def upload_acceptance(attachment_id: int = None):
    """
    Ingests completed and stamped Acceptance Form scan (PRD Pipeline 2).
    """
    if attachment_id is None:
        attachment_id = request.form.get('attachment_id', type=int)

    if attachment_id:
        attachment = _get_student_attachment_or_404(attachment_id)
    elif current_user.student_master and current_user.student_master.attachments.count() > 0:
        attachment = current_user.student_master.attachments.order_by(AttachmentRecord.created_at.desc()).first()
    else:
        flash('No active attachment found to upload acceptance for.', 'danger')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        file_obj = request.files.get('acceptance_scan') or request.files.get('acceptance_file')
        if not file_obj or file_obj.filename == '':
            flash('Please select a scanned document (PDF, PNG, JPG, or JPEG) to upload.', 'danger')
            return render_template('student/upload_acceptance.html', attachment=attachment)

        supervisor_phone = (request.form.get('workplace_supervisor_phone') or request.form.get('supervisor_phone') or request.form.get('telephone') or request.form.get('phone') or '').strip()
        supervisor_name = (request.form.get('workplace_supervisor_name') or request.form.get('supervisor_name') or request.form.get('contact_person') or '').strip()
        region = (request.form.get('region') or '').strip()
        district_town = (request.form.get('district_town') or '').strip()
        gps_address = (request.form.get('gps_address') or request.form.get('postal_address') or '').strip()
        landmark = (request.form.get('landmark') or '').strip()
        lat_val = request.form.get('latitude')
        lng_val = request.form.get('longitude')

        org_data = {
            'organization_name': (request.form.get('organization_name') or request.form.get('host_organization_name') or request.form.get('company_name') or '').strip(),
            'organization_type': (request.form.get('organization_type') or request.form.get('sector_type') or request.form.get('industry_sector') or 'Private').strip(),
            'location': (request.form.get('location') or request.form.get('industry_location') or district_town or '').strip(),
            'postal_address': (request.form.get('postal_address') or gps_address or '').strip(),
            'telephone': supervisor_phone,
            'email': request.form.get('email', '').strip(),
            'contact_person': supervisor_name,
            'workplace_supervisor_name': supervisor_name,
            'workplace_supervisor_phone': supervisor_phone,
            'region': region or None,
            'district_town': district_town or None,
            'gps_address': gps_address or None,
            'landmark': landmark or None,
            'latitude': float(lat_val) if lat_val not in (None, '') else None,
            'longitude': float(lng_val) if lng_val not in (None, '') else None,
        }

        # Validate required fields
        if not org_data['organization_name'] or not org_data['location'] or not org_data['telephone']:
            flash('Organization name, location, and contact telephone are required.', 'danger')
            return render_template('student/upload_acceptance.html', attachment=attachment)

        try:
            # 5MB maximum file size limit enforcement per PRD Pipeline 2
            max_bytes = min(5 * 1024 * 1024, current_app.config.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
            AttachmentService.process_acceptance_upload(
                attachment_id=attachment.id,
                user_id=current_user.id,
                org_data=org_data,
                file_obj=file_obj,
                storage_service=current_app.storage_service,
                allowed_extensions=current_app.config['ALLOWED_EXTENSIONS'],
                allowed_mimes=current_app.config['ALLOWED_MIME_TYPES'],
                max_size=max_bytes
            )
            # Transition status to PENDING_VERIFICATION
            attachment.status = AttachmentStatus.PENDING_VERIFICATION
            db.session.commit()

            flash('Acceptance Form uploaded successfully! Status updated to Pending Verification. The Liaison Unit will review the official wet-ink stamp and endorsement.', 'success')
            return redirect(url_for('student.dashboard'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'An unexpected error occurred during upload: {str(e)}', 'danger')

    return render_template('student/upload_acceptance.html', attachment=attachment)


@student_bp.route('/attachment/<int:attachment_id>/acceptance/scan/<int:acceptance_id>')
@login_required
@student_required
def view_uploaded_scan(attachment_id: int, acceptance_id: int):
    attachment = _get_student_attachment_or_404(attachment_id)
    acceptance = AcceptanceRecord.query.get_or_404(acceptance_id)
    if acceptance.attachment_id != attachment.id:
        abort(403)

    file_bytes = current_app.storage_service.retrieve(acceptance.storage_key)
    if not file_bytes:
        abort(404)

    return send_file(
        io.BytesIO(file_bytes),
        mimetype=acceptance.mime_type,
        as_attachment=False
    )


@student_bp.route('/attachment/<int:attachment_id>/activities')
@login_required
@student_required
def activities(attachment_id: int):
    attachment = _get_student_attachment_or_404(attachment_id)
    require_approval = current_app.config.get('REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING', False)
    if not attachment.can_log_activities(require_approval):
        flash('Activity logging is currently locked. You must upload your endorsed Acceptance Form (and receive approval if required by policy).', 'warning')
        return redirect(url_for('student.view_attachment', attachment_id=attachment.id))

    # Selected week (defaults to 1)
    week_num = request.args.get('week', 1, type=int)
    selected_week = WeeklyActivity.query.filter_by(
        attachment_id=attachment.id,
        week_number=week_num
    ).first()

    if not selected_week and attachment.weekly_activities:
        selected_week = attachment.weekly_activities[0]

    all_weeks = WeeklyActivity.query.filter_by(
        attachment_id=attachment.id
    ).order_by(WeeklyActivity.week_number).all()

    return render_template(
        'student/activities.html',
        attachment=attachment,
        all_weeks=all_weeks,
        selected_week=selected_week
    )


@student_bp.route('/activities/entry/<int:entry_id>/update', methods=['POST'])
@login_required
@student_required
def update_daily_entry(entry_id: int):
    """
    Saves or updates daily activity.
    Strictly rejected if the week is locked!
    """
    entry = DailyActivity.query.get_or_404(entry_id)
    weekly = entry.weekly_activity
    _get_student_attachment_or_404(weekly.attachment_id)

    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    key_tasks = request.form.get('key_tasks', '').strip()
    skills_demonstrated = request.form.get('skills_demonstrated', '').strip()
    remarks = request.form.get('remarks', '').strip()

    try:
        AttachmentService.update_daily_activity(
            daily_activity_id=entry.id,
            student_user_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            key_tasks=key_tasks,
            skills_demonstrated=skills_demonstrated,
            remarks=remarks
        )
        flash(f'{entry.day_of_week} activity entry updated successfully.', 'success')
    except PermissionError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f'Failed to update entry: {str(e)}', 'danger')

    return redirect(url_for('student.activities', attachment_id=weekly.attachment_id, week=weekly.week_number))


@student_bp.route('/activities/week/<int:week_id>/lock', methods=['POST'])
@student_bp.route('/attachment/week/<int:week_id>/lock', methods=['POST'])
@login_required
@student_required
def lock_week(week_id: int):
    """
    Student-controlled weekly lock (PRD Section 23).
    Once locked, the week becomes permanently read-only on the server.
    """
    weekly = WeeklyActivity.query.get_or_404(week_id)
    _get_student_attachment_or_404(weekly.attachment_id)

    try:
        AttachmentService.lock_week(
            weekly_activity_id=weekly.id,
            student_user_id=current_user.id
        )
        flash(f'Week {weekly.week_number} has been locked successfully! The entries are now read-only. Please download and print your Weekly Activity Sheet for physical workplace supervisor endorsement.', 'success')
    except PermissionError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f'Failed to lock week: {str(e)}', 'danger')

    return redirect(url_for('student.activities', attachment_id=weekly.attachment_id, week=weekly.week_number))


@student_bp.route('/activities/week/<int:week_id>/sheet')
@student_bp.route('/attachment/week/<int:week_id>/download-sheet')
@login_required
@student_required
def download_weekly_sheet(week_id: int):
    """
    Generates and downloads the official Weekly Activity Sheet PDF with the
    designated Physical Supervisor Verification Section (PRD Section 24 & 25).
    """
    weekly = WeeklyActivity.query.get_or_404(week_id)
    attachment = _get_student_attachment_or_404(weekly.attachment_id)

    pdf_bytes = PDFService.generate_weekly_activity_sheet(weekly)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Weekly_Sheet_Week{weekly.week_number}_{attachment.student.index_number.replace('/', '_')}.pdf"
    )


@student_bp.route('/attachment/<int:attachment_id>/compiled-report')
@login_required
@student_required
def download_compiled_report(attachment_id: int):
    """
    Generates and downloads the multi-week compiled activity report (PRD Section 26).
    """
    attachment = _get_student_attachment_or_404(attachment_id)
    pdf_bytes = PDFService.generate_multi_week_compilation(attachment)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Compiled_WEL_Logbook_{attachment.student.index_number.replace('/', '_')}.pdf"
    )


@student_bp.route('/attachment/<int:attachment_id>/launch-elogsheet')
@student_bp.route('/attachment/<int:attachment_id>/launch-elogbook')
@login_required
@student_required
def launch_elogsheet(attachment_id: int):
    """
    Decoupled eLogBook Single Sign-On (SSO) Gateway (Pipeline 5).
    Issues a cryptographically signed HMAC-SHA256 JWT with a 120-second expiration window
    and redirects the student to the decoupled external eLogBook application.
    """
    attachment = _get_student_attachment_or_404(attachment_id)
    student = attachment.student

    secret_key = current_app.config.get('SECRET_KEY', 'dev-secret-key-u-iap-2026')
    sso_token = generate_elogbook_sso_jwt(student, attachment, secret_key, expires_in=120)

    external_base = current_app.config.get('EXTERNAL_ELOGBOOK_URL', 'https://usted-elogbook.vercel.app').rstrip('/')
    sso_redirect_url = f"{external_base}?sso_token={sso_token}"

    flash("Redirecting to your secure external eLogBook session...", "info")
    return redirect(sso_redirect_url)


@student_bp.route('/attachment/<int:attachment_id>/assessment-form/download')
@student_bp.route('/attachment/<int:attachment_id>/assessment-form')
@login_required
@student_required
def download_assessment_form(attachment_id: int):
    """
    Generates and downloads the official 2-page Confidential 20-Item Assessment Form (Pipeline 6).
    """
    attachment = _get_student_attachment_or_404(attachment_id)
    pdf_bytes = PDFService.generate_confidential_assessment_form(attachment)
    idx_str = attachment.student.index_number.replace('/', '_')
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Confidential_WEL_Assessment_Form_{idx_str}.pdf"
    )


@student_bp.route('/documents/blank-acceptance-form', endpoint='download_blank_acceptance_template')
@student_bp.route('/documents/blank-acceptance-form-generic', endpoint='download_generic_blank_acceptance')
@login_required
def download_blank_acceptance_template():
    """Download unpopulated blank WEL Acceptance Form."""
    pdf_bytes = PDFService.generate_acceptance_form_template(None)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name="WEL_Blank_Acceptance_Form.pdf"
    )


@student_bp.route('/documents/blank-assessment-form', endpoint='download_blank_assessment_template')
@student_bp.route('/documents/blank-assessment-form-generic', endpoint='download_generic_blank_assessment')
@login_required
def download_blank_assessment_template():
    """Download unpopulated blank Confidential Assessment Form."""
    pdf_bytes = PDFService.generate_confidential_assessment_form(None)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name="Confidential_WEL_Assessment_Form_Blank.pdf"
    )


