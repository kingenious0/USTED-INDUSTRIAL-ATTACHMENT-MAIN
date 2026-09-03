from datetime import datetime, timezone
import json
from app.extensions import db


class AuditAction:
    USER_LOGIN = 'USER_LOGIN'
    USER_LOGOUT = 'USER_LOGOUT'
    STUDENT_LOOKUP = 'STUDENT_LOOKUP'
    ATTACHMENT_INITIATED = 'ATTACHMENT_INITIATED'
    ATTACHMENT_STATUS_CHANGE = 'ATTACHMENT_STATUS_CHANGE'
    LETTER_GENERATED = 'LETTER_GENERATED'
    LETTER_REPRINTED = 'LETTER_REPRINTED'
    ACCEPTANCE_UPLOADED = 'ACCEPTANCE_UPLOADED'
    ACCEPTANCE_REVIEWED = 'ACCEPTANCE_REVIEWED'
    ACTIVITY_UPDATED = 'ACTIVITY_UPDATED'
    WEEK_LOCKED = 'WEEK_LOCKED'
    WEEK_UNLOCKED = 'WEEK_UNLOCKED'
    DOCUMENT_GENERATED = 'DOCUMENT_GENERATED'
    CONFIG_CHANGED = 'CONFIG_CHANGED'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    actor_username = db.Column(db.String(80), nullable=True)
    actor_role = db.Column(db.String(30), nullable=True)
    
    action = db.Column(db.String(60), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=True, index=True)
    target_id = db.Column(db.Integer, nullable=True, index=True)
    
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    actor = db.relationship('User', foreign_keys=[actor_id])

    @property
    def details(self):
        if not self.details_json:
            return {}
        try:
            return json.loads(self.details_json)
        except Exception:
            return {'raw': self.details_json}

    @details.setter
    def details(self, value):
        self.details_json = json.dumps(value) if value is not None else None

    def __repr__(self):
        return f"<AuditLog #{self.id} [{self.action}] by User #{self.actor_id} at {self.timestamp}>"
