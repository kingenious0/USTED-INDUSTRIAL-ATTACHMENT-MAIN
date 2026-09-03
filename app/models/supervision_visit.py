from datetime import datetime, timezone
from app.extensions import db


class SupervisionVisit(db.Model):
    __tablename__ = 'supervision_visits'

    id = db.Column(db.Integer, primary_key=True)
    attachment_id = db.Column(db.Integer, db.ForeignKey('attachment_records.id'), nullable=False, index=True)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    visit_date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    visit_type = db.Column(db.String(50), default='Physical In-Person', nullable=False)
    supervisor_contacted = db.Column(db.String(150), nullable=True)
    student_present = db.Column(db.Boolean, default=True, nullable=False)
    
    # Evaluation and comments
    general_remarks = db.Column(db.Text, nullable=True)
    action_items = db.Column(db.Text, nullable=True)
    follow_up_needed = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    attachment = db.relationship('AttachmentRecord', back_populates='supervision_visits')
    lecturer = db.relationship('User', foreign_keys=[lecturer_id])

    def __repr__(self):
        return f"<SupervisionVisit #{self.id} for Attachment #{self.attachment_id} by Lecturer #{self.lecturer_id}>"
