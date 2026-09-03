from datetime import datetime, timezone
from app.extensions import db


class AttachmentStatus:
    INITIATED = 'initiated'
    LETTER_GENERATED = 'letter_generated'
    LETTER_ISSUED = 'letter_issued'
    ACCEPTANCE_PENDING = 'acceptance_pending'
    ACCEPTANCE_UPLOADED = 'acceptance_uploaded'
    PENDING_VERIFICATION = 'pending_verification'
    ACCEPTANCE_APPROVED = 'acceptance_approved'
    ACCEPTANCE_FLAGGED = 'acceptance_flagged'
    LOGGING_ACTIVE = 'logging_active'
    COMPLETED = 'completed'


class AttachmentRecord(db.Model):
    __tablename__ = 'attachment_records'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_masters.id'), nullable=False, index=True)
    academic_year = db.Column(db.String(20), nullable=False)  # e.g. "2025/2026"
    duration_weeks = db.Column(db.Integer, nullable=False, default=8)
    commencement_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default=AttachmentStatus.INITIATED, nullable=False, index=True)

    # Organization details (can be initially set during letter generation or confirmed upon acceptance)
    target_organization = db.Column(db.String(200), nullable=True)
    organization_address = db.Column(db.String(255), nullable=True)

    # Supervision assignment
    academic_supervisor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    academic_supervisor = db.relationship('User', foreign_keys=[academic_supervisor_id])

    # Administrative audit metadata
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    student = db.relationship('StudentMaster', back_populates='attachments')
    letters = db.relationship(
        'IntroductoryLetter',
        back_populates='attachment',
        cascade='all, delete-orphan',
        order_by='desc(IntroductoryLetter.created_at)'
    )
    acceptance_records = db.relationship(
        'AcceptanceRecord',
        back_populates='attachment',
        cascade='all, delete-orphan',
        order_by='desc(AcceptanceRecord.created_at)'
    )
    weekly_activities = db.relationship(
        'WeeklyActivity',
        back_populates='attachment',
        cascade='all, delete-orphan',
        order_by='WeeklyActivity.week_number'
    )
    documents = db.relationship(
        'Document',
        back_populates='attachment',
        cascade='all, delete-orphan',
        order_by='desc(Document.created_at)'
    )

    @property
    def latest_acceptance(self):
        return self.acceptance_records[0] if self.acceptance_records else None

    @property
    def latest_letter(self):
        return self.letters[0] if self.letters else None

    @property
    def introductory_letters(self):
        return self.letters

    @property
    def is_letter_issued(self) -> bool:
        return self.status in (AttachmentStatus.LETTER_ISSUED, AttachmentStatus.LETTER_GENERATED)

    @property
    def is_pending_verification(self) -> bool:
        return self.status in (AttachmentStatus.PENDING_VERIFICATION, AttachmentStatus.ACCEPTANCE_UPLOADED)

    @property
    def is_logging_active(self) -> bool:
        return self.status in (AttachmentStatus.LOGGING_ACTIVE, AttachmentStatus.ACCEPTANCE_APPROVED)

    def can_log_activities(self, require_approval: bool = False) -> bool:
        """
        Determines whether the student can enter daily activities.
        If require_approval is True:
            Requires acceptance form to be approved / logging active.
        If False:
            Requires acceptance form to be uploaded or logging status to be active.
        """
        if require_approval:
            return self.status in (
                AttachmentStatus.ACCEPTANCE_APPROVED,
                AttachmentStatus.LOGGING_ACTIVE,
                AttachmentStatus.COMPLETED
            )
        # Option B: Asynchronous review allowed
        return self.status in (
            AttachmentStatus.ACCEPTANCE_UPLOADED,
            AttachmentStatus.PENDING_VERIFICATION,
            AttachmentStatus.ACCEPTANCE_APPROVED,
            AttachmentStatus.LOGGING_ACTIVE,
            AttachmentStatus.COMPLETED
        )

    def __repr__(self):
        return f"<AttachmentRecord #{self.id} [Student: {self.student_id}] ({self.status})>"
