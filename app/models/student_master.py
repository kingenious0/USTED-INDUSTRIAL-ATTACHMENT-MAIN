from datetime import datetime, timezone
from app.extensions import db


class StudentMaster(db.Model):
    __tablename__ = 'student_masters'

    id = db.Column(db.Integer, primary_key=True)
    index_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    programme = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(150), nullable=False)
    current_level = db.Column(db.Integer, nullable=False)  # 100, 200, 300, 400
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship to AttachmentRecords (1:M per PRD Section 13: student may undertake multiple attachments)
    attachments = db.relationship(
        'AttachmentRecord',
        back_populates='student',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<StudentMaster {self.index_number} - {self.full_name}>"
