from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.attachment import AttachmentRecord, AttachmentStatus
from app.models.letter import IntroductoryLetter
from app.models.acceptance import AcceptanceRecord, AcceptanceStatus
from app.models.activity import WeeklyActivity, DailyActivity, DayOfWeek
from app.models.document import Document, DocumentType
from app.models.audit import AuditAction
from app.services.storage import StorageService
from app.services.pdf_service import PDFService
from app.services.audit_service import AuditService
from app.utils.tokens import generate_qr_token


class AttachmentService:

    @staticmethod
    def create_attachment(
        student_id: int,
        academic_year: str,
        duration_weeks: int,
        commencement_date,
        end_date,
        created_by_id: int,
        target_organization: str = None,
        organization_address: str = None
    ) -> AttachmentRecord:
        """
        Creates an attachment record after in-person student verification (PRD Section 13, 15).
        Automatically provisions empty weekly activity sheets and Mon-Fri slots.
        """
        attachment = AttachmentRecord(
            student_id=student_id,
            academic_year=academic_year,
            duration_weeks=duration_weeks,
            commencement_date=commencement_date,
            end_date=end_date,
            target_organization=target_organization,
            organization_address=organization_address,
            created_by_id=created_by_id,
            status=AttachmentStatus.INITIATED
        )
        db.session.add(attachment)
        db.session.flush()

        # Provision weekly structure (Monday - Friday)
        curr_monday = commencement_date
        # Align to Monday if start date is not already Monday
        if curr_monday.weekday() != 0:
            curr_monday = curr_monday - timedelta(days=curr_monday.weekday())

        for week_num in range(1, duration_weeks + 1):
            week_start = curr_monday
            week_end = curr_monday + timedelta(days=4) # Friday

            weekly_act = WeeklyActivity(
                attachment_id=attachment.id,
                week_number=week_num,
                start_date=week_start,
                end_date=week_end,
                is_locked=False
            )
            db.session.add(weekly_act)
            db.session.flush()

            for day_offset, day_name in enumerate(DayOfWeek.WEEKDAYS):
                day_date = week_start + timedelta(days=day_offset)
                daily_act = DailyActivity(
                    weekly_activity_id=weekly_act.id,
                    day_of_week=day_name,
                    date=day_date,
                    start_time='08:00',
                    end_time='17:00',
                    key_tasks='',
                    skills_demonstrated='',
                    remarks=''
                )
                db.session.add(daily_act)

            curr_monday = curr_monday + timedelta(days=7)

        db.session.commit()

        AuditService.log(
            action=AuditAction.ATTACHMENT_INITIATED,
            target_type='AttachmentRecord',
            target_id=attachment.id,
            details={
                'student_id': student_id,
                'duration_weeks': duration_weeks,
                'academic_year': academic_year
            }
        )
        return attachment

    @staticmethod
    def generate_or_reprint_letter(
        attachment_id: int,
        user_id: int,
        storage_service: StorageService,
        addressee_org: str = None,
        config: dict = None
    ) -> Tuple[IntroductoryLetter, bytes]:
        """
        Generates or reprints the official Introductory Letter via ReportLab.
        Adheres to PRD Section 16.
        """
        attachment = AttachmentRecord.query.get_or_404(attachment_id)
        if addressee_org:
            attachment.target_organization = addressee_org

        existing_letter = attachment.latest_letter
        if existing_letter:
            # Reprint workflow
            existing_letter.reprint_count += 1
            if addressee_org:
                existing_letter.addressee_organization = addressee_org
            letter_record = existing_letter
            action = AuditAction.LETTER_REPRINTED
        else:
            # New letter generation
            ref_num = f"USTED/ILU/{attachment.academic_year.replace('/', '-')}/{attachment.id:04d}"
            storage_key = f"letters/intro_letter_{attachment.id}_{int(datetime.now().timestamp())}.pdf"
            letter_record = IntroductoryLetter(
                attachment_id=attachment.id,
                reference_number=ref_num,
                letter_date=datetime.now().date(),
                addressee_organization=addressee_org or attachment.target_organization,
                storage_key=storage_key,
                generated_by_id=user_id
            )
            db.session.add(letter_record)
            if attachment.status == AttachmentStatus.INITIATED:
                attachment.status = AttachmentStatus.LETTER_GENERATED
            action = AuditAction.LETTER_GENERATED

        db.session.flush()

        # Generate PDF via ReportLab with embedded 24-hour verification QR code
        liaison_name = config.get('LIAISON_HEAD_NAME') if config else None
        liaison_title = config.get('LIAISON_HEAD_TITLE') if config else None
        secret_key = config.get('SECRET_KEY', 'dev-secret-key-u-iap-2026') if config else 'dev-secret-key-u-iap-2026'

        qr_token = generate_qr_token(attachment.student.index_number, secret_key)
        qr_access_url = f"/portal/access/{attachment.student.index_number}?token={qr_token}"

        pdf_bytes = PDFService.generate_introductory_letter(
            attachment,
            letter_record,
            liaison_head_name=liaison_name,
            liaison_head_title=liaison_title,
            qr_access_url=qr_access_url
        )

        # Save to storage service
        storage_service.save(pdf_bytes, letter_record.storage_key)

        # Record document metadata
        doc = Document(
            attachment_id=attachment.id,
            doc_type=DocumentType.INTRODUCTORY_LETTER,
            title=f"Introductory Letter ({letter_record.reference_number})",
            original_filename=f"Introductory_Letter_{attachment.student.index_number.replace('/', '_')}.pdf",
            storage_key=letter_record.storage_key,
            mime_type='application/pdf',
            file_size_bytes=len(pdf_bytes),
            created_by_id=user_id
        )
        db.session.add(doc)
        db.session.commit()

        AuditService.log(
            action=action,
            target_type='IntroductoryLetter',
            target_id=letter_record.id,
            details={
                'reference_number': letter_record.reference_number,
                'reprint_count': letter_record.reprint_count
            }
        )
        return letter_record, pdf_bytes

    @staticmethod
    def process_acceptance_upload(
        attachment_id: int,
        user_id: int,
        org_data: Dict[str, Any],
        file_obj: FileStorage,
        storage_service: StorageService,
        allowed_extensions: set,
        allowed_mimes: set,
        max_size: int
    ) -> AcceptanceRecord:
        """
        Validates, stores, and records student's completed physical Acceptance Form scan.
        Adheres to PRD Section 18.
        """
        attachment = AttachmentRecord.query.get_or_404(attachment_id)

        # Server-side validation (PRD Section 18)
        filename = secure_filename(file_obj.filename or '')
        if not filename or '.' not in filename:
            raise ValueError("Invalid file. Please provide a valid file with an extension.")

        ext = filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            raise ValueError(f"File type '.{ext}' is not permitted. Allowed formats: PDF, PNG, JPG, JPEG.")

        # Read contents to verify size and MIME
        file_bytes = file_obj.read()
        if len(file_bytes) > max_size:
            raise ValueError(f"File size ({len(file_bytes) // 1024} KB) exceeds maximum permitted limit ({max_size // 1024} KB).")

        content_type = file_obj.content_type
        # Verify MIME type matches whitelist
        if content_type and content_type not in allowed_mimes:
            # Fallback check for jpeg/pjpeg
            if ext in ('jpg', 'jpeg') and content_type in ('image/jpeg', 'image/pjpeg', 'application/octet-stream'):
                content_type = 'image/jpeg'
            elif ext == 'pdf' and content_type in ('application/pdf', 'application/x-pdf', 'application/octet-stream'):
                content_type = 'application/pdf'
            else:
                raise ValueError(f"Content type '{content_type}' is not recognized as a valid scan format.")

        storage_key = f"acceptance/scan_{attachment.id}_{int(datetime.now().timestamp())}.{ext}"
        storage_service.save(file_bytes, storage_key)

        acceptance = AcceptanceRecord(
            attachment_id=attachment.id,
            organization_name=(org_data.get('organization_name') or '').strip(),
            organization_type=(org_data.get('organization_type') or '').strip(),
            location=(org_data.get('location') or '').strip(),
            postal_address=(org_data.get('postal_address') or '').strip(),
            telephone=(org_data.get('telephone') or '').strip(),
            email=(org_data.get('email') or '').strip(),
            contact_person=(org_data.get('contact_person') or '').strip(),
            workplace_supervisor_name=(org_data.get('workplace_supervisor_name') or org_data.get('supervisor_name') or '').strip(),
            workplace_supervisor_phone=(org_data.get('workplace_supervisor_phone') or org_data.get('supervisor_phone') or '').strip(),
            region=(org_data.get('region') or '').strip() or None,
            district_town=(org_data.get('district_town') or '').strip() or None,
            gps_address=(org_data.get('gps_address') or '').strip() or None,
            landmark=(org_data.get('landmark') or '').strip() or None,
            latitude=float(org_data['latitude']) if org_data.get('latitude') not in (None, '') else None,
            longitude=float(org_data['longitude']) if org_data.get('longitude') not in (None, '') else None,
            original_filename=filename,
            storage_key=storage_key,
            mime_type=content_type or 'application/octet-stream',

            file_size_bytes=len(file_bytes),
            uploaded_by_id=user_id,
            status=AcceptanceStatus.PENDING_REVIEW
        )
        db.session.add(acceptance)

        # Update attachment organization details and status
        attachment.target_organization = acceptance.organization_name
        attachment.organization_address = acceptance.location
        attachment.status = AttachmentStatus.ACCEPTANCE_UPLOADED

        # Record Document
        doc = Document(
            attachment_id=attachment.id,
            doc_type=DocumentType.ACCEPTANCE_UPLOADED_SCAN,
            title=f"Uploaded Acceptance Scan ({acceptance.organization_name})",
            original_filename=filename,
            storage_key=storage_key,
            mime_type=content_type or 'application/octet-stream',
            file_size_bytes=len(file_bytes),
            created_by_id=user_id
        )
        db.session.add(doc)
        db.session.commit()

        AuditService.log(
            action=AuditAction.ACCEPTANCE_UPLOADED,
            target_type='AcceptanceRecord',
            target_id=acceptance.id,
            details={
                'organization': acceptance.organization_name,
                'filename': filename,
                'file_size': len(file_bytes)
            }
        )
        return acceptance

    @staticmethod
    def review_acceptance(
        acceptance_id: int,
        reviewer_id: int,
        status: str,
        review_notes: str = None,
        has_signature: bool = False,
        has_stamp: bool = False
    ) -> AcceptanceRecord:
        """
        Liaison Officer reviews uploaded Acceptance Form scan.
        Adheres to PRD Section 19 & 43.
        """
        acceptance = AcceptanceRecord.query.get_or_404(acceptance_id)
        attachment = acceptance.attachment

        acceptance.status = status
        acceptance.review_notes = review_notes
        acceptance.has_supervisor_signature = has_signature
        acceptance.has_official_stamp = has_stamp
        acceptance.reviewed_by_id = reviewer_id
        acceptance.reviewed_at = datetime.now(timezone.utc)

        if status == AcceptanceStatus.APPROVED:
            attachment.status = AttachmentStatus.ACCEPTANCE_APPROVED
        elif status in (AcceptanceStatus.FLAGGED_BLURRY, AcceptanceStatus.FLAGGED_INCOMPLETE, AcceptanceStatus.REJECTED):
            attachment.status = AttachmentStatus.ACCEPTANCE_FLAGGED

        db.session.commit()

        AuditService.log(
            action=AuditAction.ACCEPTANCE_REVIEWED,
            target_type='AcceptanceRecord',
            target_id=acceptance.id,
            details={
                'review_status': status,
                'has_signature': has_signature,
                'has_stamp': has_stamp,
                'notes': review_notes
            }
        )
        return acceptance

    @staticmethod
    def update_daily_activity(
        daily_activity_id: int,
        student_user_id: int,
        start_time: str,
        end_time: str,
        key_tasks: str,
        skills_demonstrated: str,
        remarks: str = None
    ) -> DailyActivity:
        """
        Updates daily activity record.
        STRICT SERVER-SIDE ENFORCEMENT (PRD Section 23):
        Rejects modifications if the week is locked or user is unauthorized!
        """
        entry = DailyActivity.query.get_or_404(daily_activity_id)
        weekly = entry.weekly_activity
        attachment = weekly.attachment

        # Authorization: Must be the student who owns this attachment
        student_master = attachment.student
        if not student_master or not student_master.user or student_master.user.id != student_user_id:
            raise PermissionError("Unauthorized: You can only edit activities for your own attachment.")

        # STRICT LOCK ENFORCEMENT
        if weekly.is_locked:
            raise PermissionError("Forbidden: This week has been locked and is strictly read-only.")

        entry.start_time = start_time
        entry.end_time = end_time
        entry.key_tasks = key_tasks
        entry.skills_demonstrated = skills_demonstrated
        entry.remarks = remarks
        db.session.commit()

        AuditService.log(
            action=AuditAction.ACTIVITY_UPDATED,
            target_type='DailyActivity',
            target_id=entry.id,
            details={
                'day': entry.day_of_week,
                'week_number': weekly.week_number
            }
        )
        return entry

    @staticmethod
    def lock_week(weekly_activity_id: int, student_user_id: int) -> WeeklyActivity:
        """
        Student-controlled weekly lock (PRD Section 23).
        Once locked, entries become permanently read-only on the server.
        """
        weekly = WeeklyActivity.query.get_or_404(weekly_activity_id)
        attachment = weekly.attachment

        # Authorization
        student_master = attachment.student
        if not student_master or not student_master.user or student_master.user.id != student_user_id:
            raise PermissionError("Unauthorized: You can only lock weeks for your own attachment.")

        if weekly.is_locked:
            return weekly

        weekly.is_locked = True
        weekly.locked_at = datetime.now(timezone.utc)
        weekly.locked_by_id = student_user_id

        # Update attachment status to logging_active if not already
        if attachment.status in (AttachmentStatus.ACCEPTANCE_APPROVED, AttachmentStatus.ACCEPTANCE_UPLOADED):
            attachment.status = AttachmentStatus.LOGGING_ACTIVE

        db.session.commit()

        AuditService.log(
            action=AuditAction.WEEK_LOCKED,
            target_type='WeeklyActivity',
            target_id=weekly.id,
            details={
                'week_number': weekly.week_number,
                'locked_at': weekly.locked_at.isoformat()
            }
        )
        return weekly
