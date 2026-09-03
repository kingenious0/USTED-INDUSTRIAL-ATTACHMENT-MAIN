from datetime import datetime, timezone
from app.extensions import db


class DocumentType:
    INTRODUCTORY_LETTER = 'introductory_letter'
    ACCEPTANCE_BLANK_FORM = 'acceptance_blank_form'
    ACCEPTANCE_UPLOADED_SCAN = 'acceptance_uploaded_scan'
    WEEKLY_ACTIVITY_SHEET = 'weekly_activity_sheet'
    COMPILED_ATTACHMENT_REPORT = 'compiled_attachment_report'


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    attachment_id = db.Column(db.Integer, db.ForeignKey('attachment_records.id'), nullable=False, index=True)
    doc_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), default='application/pdf', nullable=False)
    file_size_bytes = db.Column(db.Integer, default=0, nullable=False)

    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    attachment = db.relationship('AttachmentRecord', back_populates='documents')

    def __repr__(self):
        return f"<Document #{self.id} [{self.doc_type}] ({self.original_filename})>"
