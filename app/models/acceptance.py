from datetime import datetime, timezone
from app.extensions import db


class AcceptanceStatus:
    PENDING_REVIEW = 'pending_review'
    APPROVED = 'approved'
    FLAGGED_BLURRY = 'flagged_blurry'
    FLAGGED_INCOMPLETE = 'flagged_incomplete'
    REJECTED = 'rejected'


class AcceptanceRecord(db.Model):
    __tablename__ = 'acceptance_records'

    id = db.Column(db.Integer, primary_key=True)
    attachment_id = db.Column(db.Integer, db.ForeignKey('attachment_records.id'), nullable=False, index=True)

    # Host organization information provided by student / extracted from form
    organization_name = db.Column(db.String(200), nullable=False)
    organization_type = db.Column(db.String(100), nullable=True)  # Public, Private, NGO, etc.
    location = db.Column(db.String(200), nullable=False)
    postal_address = db.Column(db.String(255), nullable=True)
    telephone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    contact_person = db.Column(db.String(150), nullable=True)
    workplace_supervisor_name = db.Column(db.String(150), nullable=True)
    workplace_supervisor_phone = db.Column(db.String(50), nullable=True)

    # Physical verification checklist captured by Liaison review
    has_supervisor_signature = db.Column(db.Boolean, default=False, nullable=False)
    has_official_stamp = db.Column(db.Boolean, default=False, nullable=False)

    # File storage metadata (PRD Section 8 & 18)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size_bytes = db.Column(db.Integer, nullable=False)

    # Workflow & review status
    status = db.Column(db.String(30), default=AcceptanceStatus.PENDING_REVIEW, nullable=False, index=True)
    review_notes = db.Column(db.Text, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])
    reviewed_at = db.Column(db.DateTime, nullable=True)

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    attachment = db.relationship('AttachmentRecord', back_populates='acceptance_records')

    @property
    def is_approved(self):
        return self.status == AcceptanceStatus.APPROVED

    @property
    def is_flagged(self):
        return self.status in (AcceptanceStatus.FLAGGED_BLURRY, AcceptanceStatus.FLAGGED_INCOMPLETE)

    def __repr__(self):
        return f"<AcceptanceRecord #{self.id} for Attachment #{self.attachment_id} ({self.status})>"
