from datetime import datetime, timezone
from app.extensions import db


class IntroductoryLetter(db.Model):
    __tablename__ = 'introductory_letters'

    id = db.Column(db.Integer, primary_key=True)
    attachment_id = db.Column(db.Integer, db.ForeignKey('attachment_records.id'), nullable=False, index=True)
    reference_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    letter_date = db.Column(db.Date, nullable=False)
    addressee_organization = db.Column(db.String(255), nullable=True)
    storage_key = db.Column(db.String(255), nullable=False)
    
    generated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    generated_by = db.relationship('User', foreign_keys=[generated_by_id])
    
    reprint_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    attachment = db.relationship('AttachmentRecord', back_populates='letters')

    def __repr__(self):
        return f"<IntroductoryLetter {self.reference_number} for Attachment #{self.attachment_id}>"
