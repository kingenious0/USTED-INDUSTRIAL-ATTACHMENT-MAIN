from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
    send_file, current_app
)
from flask_login import login_required, current_user
import io
from app.extensions import db
from app.models.student_master import StudentMaster
from app.models.attachment import AttachmentRecord, AttachmentStatus
from app.models.acceptance import AcceptanceRecord, AcceptanceStatus
from app.models.letter import IntroductoryLetter
from app.models.user import User, UserRole
from app.services.attachment_service import AttachmentService
from app.services.pdf_service import PDFService
from app.utils.decorators import liaison_required

liaison_bp = Blueprint('liaison', __name__)


@liaison_bp.route('/dashboard')
@login_required
@liaison_required
def dashboard():
    total_attachments = AttachmentRecord.query.count()
    pending_acceptance = AcceptanceRecord.query.filter_by(status=AcceptanceStatus.PENDING_REVIEW).count()
    active_logging = AttachmentRecord.query.filter(
        AttachmentRecord.status.in_([AttachmentStatus.LOGGING_ACTIVE, AttachmentStatus.ACCEPTANCE_APPROVED])
    ).count()
    completed = AttachmentRecord.query.filter_by(status=AttachmentStatus.COMPLETED).count()

    recent_attachments = AttachmentRecord.query.order_by(AttachmentRecord.created_at.desc()).limit(8).all()
    pending_reviews = AcceptanceRecord.query.filter_by(
        status=AcceptanceStatus.PENDING_REVIEW
    ).order_by(AcceptanceRecord.created_at.asc()).limit(5).all()

    return render_template(
        'liaison/dashboard.html',
        total_attachments=total_attachments,
        pending_acceptance=pending_acceptance,
        active_logging=active_logging,
        completed=completed,
        recent_attachments=recent_attachments,
        pending_reviews=pending_reviews
    )


@liaison_bp.route('/students/lookup', methods=['GET', 'POST'])
@login_required
@liaison_required
def student_lookup():
    """
    Search student master records primarily using University Index Number (PRD Section 12).
    """
    query = request.args.get('q', '').strip()
    students = []
    if query:
        students = StudentMaster.query.filter(
            (StudentMaster.index_number.ilike(f"%{query}%")) |
            (StudentMaster.full_name.ilike(f"%{query}%"))
        ).all()

    return render_template('liaison/student_lookup.html', query=query, students=students)


@liaison_bp.route('/verify-and-create/<int:student_id>', methods=['GET', 'POST'])
@login_required
@liaison_required
def verify_and_create_attachment(student_id: int):
    """
    Mandatory Physical Liaison Office Checkpoint (PRD Section 15).
    Liaison Officer confirms student identity and initiates attachment record.
    """
    student = StudentMaster.query.get_or_404(student_id)

    if request.method == 'POST':
        academic_year = request.form.get('academic_year', '').strip()
        duration_weeks = request.form.get('duration_weeks', 8, type=int)
        commence_str = request.form.get('commencement_date', '').strip()
        target_org = request.form.get('target_organization', '').strip()
        org_address = request.form.get('organization_address', '').strip()

        try:
            commence_date = datetime.strptime(commence_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid commencement date format.', 'danger')
            return render_template('liaison/verify_and_create.html', student=student)

        end_date = commence_date + timedelta(weeks=duration_weeks)

        # Create attachment and provision weekly sheets
        attachment = AttachmentService.create_attachment(
            student_id=student.id,
            academic_year=academic_year,
            duration_weeks=duration_weeks,
            commencement_date=commence_date,
            end_date=end_date,
            created_by_id=current_user.id,
            target_organization=target_org,
            organization_address=org_address
        )

        # Immediately generate Introductory Letter (PRD Section 16)
        letter, _ = AttachmentService.generate_or_reprint_letter(
            attachment_id=attachment.id,
            user_id=current_user.id,
            storage_service=current_app.storage_service,
            addressee_org=target_org,
            config=current_app.config
        )

        flash(f'Student physically verified! Attachment record #{attachment.id} created and Introductory Letter ({letter.reference_number}) generated.', 'success')
        return redirect(url_for('liaison.view_attachment_detail', attachment_id=attachment.id))

    # Pre-fill academic year
    now = datetime.now()
    default_acad_year = f"{now.year}/{now.year + 1}"
    default_commence = (now + timedelta(days=(7 - now.weekday()))).strftime('%Y-%m-%d') # Next Monday

    return render_template(
        'liaison/verify_and_create.html',
        student=student,
        default_academic_year=default_acad_year,
        default_commencement=default_commence
    )


@liaison_bp.route('/attachments')
@login_required
@liaison_required
def attachments_list():
    """Roster of all attachment records with status filtering."""
    status_filter = request.args.get('status', '').strip()
    query = AttachmentRecord.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    attachments = query.order_by(AttachmentRecord.created_at.desc()).all()
    return render_template(
        'liaison/attachments_list.html',
        attachments=attachments,
        selected_status=status_filter
    )


@liaison_bp.route('/attachment/<int:attachment_id>')
@login_required
@liaison_required
def view_attachment_detail(attachment_id: int):
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    supervisors = User.query.filter_by(role=UserRole.ACADEMIC_SUPERVISOR, is_active=True).all()
    return render_template(
        'liaison/attachment_detail.html',
        attachment=attachment,
        supervisors=supervisors
    )


@liaison_bp.route('/attachment/<int:attachment_id>/reprint-letter', methods=['POST'])
@login_required
@liaison_required
def reprint_letter(attachment_id: int):
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    addressee = request.form.get('target_organization', '').strip()

    letter, _ = AttachmentService.generate_or_reprint_letter(
        attachment_id=attachment.id,
        user_id=current_user.id,
        storage_service=current_app.storage_service,
        addressee_org=addressee,
        config=current_app.config
    )
    flash(f'Introductory Letter ({letter.reference_number}) regenerated/reprinted successfully (Reprint count: {letter.reprint_count}).', 'success')
    return redirect(url_for('liaison.view_attachment_detail', attachment_id=attachment.id))


@liaison_bp.route('/attachment/<int:attachment_id>/assign-supervisor', methods=['POST'])
@login_required
@liaison_required
def assign_supervisor(attachment_id: int):
    attachment = AttachmentRecord.query.get_or_404(attachment_id)
    supervisor_id = request.form.get('supervisor_id', type=int)

    if supervisor_id:
        supervisor = User.query.get(supervisor_id)
        if supervisor and supervisor.role == UserRole.ACADEMIC_SUPERVISOR:
            attachment.academic_supervisor_id = supervisor.id
            db.session.commit()
            flash(f'Academic Supervisor {supervisor.full_name} assigned successfully.', 'success')
        else:
            flash('Invalid supervisor selected.', 'danger')
    else:
        attachment.academic_supervisor_id = None
        db.session.commit()
        flash('Supervisor assignment removed.', 'info')

    return redirect(url_for('liaison.view_attachment_detail', attachment_id=attachment.id))


@liaison_bp.route('/acceptance/queue')
@login_required
@liaison_required
def acceptance_queue():
    """Queue of uploaded Acceptance Forms awaiting official review."""
    pending_items = AcceptanceRecord.query.filter_by(
        status=AcceptanceStatus.PENDING_REVIEW
    ).order_by(AcceptanceRecord.created_at.asc()).all()

    reviewed_items = AcceptanceRecord.query.filter(
        AcceptanceRecord.status != AcceptanceStatus.PENDING_REVIEW
    ).order_by(AcceptanceRecord.reviewed_at.desc()).limit(15).all()

    return render_template(
        'liaison/acceptance_queue.html',
        pending_items=pending_items,
        reviewed_items=reviewed_items
    )


@liaison_bp.route('/acceptance/review/<int:acceptance_id>', methods=['GET', 'POST'])
@login_required
@liaison_required
def review_acceptance(acceptance_id: int):
    """
    Reviews uploaded Acceptance Form scan.
    Adheres to PRD Section 19 & 43 (missing stamp/blurry checks).
    """
    acceptance = AcceptanceRecord.query.get_or_404(acceptance_id)

    if request.method == 'POST':
        decision = request.form.get('decision')
        notes = request.form.get('review_notes', '').strip()
        has_signature = bool(request.form.get('has_supervisor_signature'))
        has_stamp = bool(request.form.get('has_official_stamp'))

        if decision == 'approve':
            if not has_stamp or not has_signature:
                flash('Cannot approve: Institutional policy requires verification of both physical supervisor signature and wet-ink company stamp.', 'danger')
                return render_template('liaison/review_acceptance.html', acceptance=acceptance)
            status = AcceptanceStatus.APPROVED
        elif decision == 'flag_blurry':
            status = AcceptanceStatus.FLAGGED_BLURRY
        elif decision == 'flag_incomplete':
            status = AcceptanceStatus.FLAGGED_INCOMPLETE
        else:
            status = AcceptanceStatus.REJECTED

        AttachmentService.review_acceptance(
            acceptance_id=acceptance.id,
            reviewer_id=current_user.id,
            status=status,
            review_notes=notes,
            has_signature=has_signature,
            has_stamp=has_stamp
        )

        flash(f'Acceptance form for {acceptance.attachment.student.full_name} reviewed with status: {status.upper()}.', 'success')
        return redirect(url_for('liaison.acceptance_queue'))

    return render_template('liaison/review_acceptance.html', acceptance=acceptance)


@liaison_bp.route('/acceptance/scan/<int:acceptance_id>')
@login_required
@liaison_required
def view_scan(acceptance_id: int):
    acceptance = AcceptanceRecord.query.get_or_404(acceptance_id)
    file_bytes = current_app.storage_service.retrieve(acceptance.storage_key)
    if not file_bytes:
        abort(404)

    return send_file(
        io.BytesIO(file_bytes),
        mimetype=acceptance.mime_type,
        as_attachment=False
    )
