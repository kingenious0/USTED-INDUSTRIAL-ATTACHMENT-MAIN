from datetime import datetime, timezone
from app.extensions import db


class DayOfWeek:
    MONDAY = 'Monday'
    TUESDAY = 'Tuesday'
    WEDNESDAY = 'Wednesday'
    THURSDAY = 'Thursday'
    FRIDAY = 'Friday'

    WEEKDAYS = [MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY]


class WeeklyActivity(db.Model):
    __tablename__ = 'weekly_activities'
    __table_args__ = (
        db.UniqueConstraint('attachment_id', 'week_number', name='uq_attachment_week'),
    )

    id = db.Column(db.Integer, primary_key=True)
    attachment_id = db.Column(db.Integer, db.ForeignKey('attachment_records.id'), nullable=False, index=True)
    week_number = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # Weekly locking controlled exclusively by student (PRD Section 23)
    is_locked = db.Column(db.Boolean, default=False, nullable=False, index=True)
    locked_at = db.Column(db.DateTime, nullable=True)
    locked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    locked_by = db.relationship('User', foreign_keys=[locked_by_id])

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    attachment = db.relationship('AttachmentRecord', back_populates='weekly_activities')
    daily_entries = db.relationship(
        'DailyActivity',
        back_populates='weekly_activity',
        cascade='all, delete-orphan',
        order_by='DailyActivity.date'
    )

    def get_entry_for_day(self, day_name: str):
        for entry in self.daily_entries:
            if entry.day_of_week == day_name:
                return entry
        return None

    def __repr__(self):
        status = "LOCKED" if self.is_locked else "UNLOCKED"
        return f"<WeeklyActivity Week #{self.week_number} [Attachment #{self.attachment_id}] ({status})>"


class DailyActivity(db.Model):
    __tablename__ = 'daily_activities'
    __table_args__ = (
        db.UniqueConstraint('weekly_activity_id', 'day_of_week', name='uq_week_day'),
    )

    id = db.Column(db.Integer, primary_key=True)
    weekly_activity_id = db.Column(db.Integer, db.ForeignKey('weekly_activities.id'), nullable=False, index=True)
    day_of_week = db.Column(db.String(15), nullable=False)  # Monday - Friday
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=True)  # e.g. "08:00"
    end_time = db.Column(db.String(10), nullable=True)    # e.g. "17:00"

    # Expandable detail fields without physical paper line constraints (PRD Section 21)
    key_tasks = db.Column(db.Text, nullable=True)
    skills_demonstrated = db.Column(db.Text, nullable=True)
    remarks = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    weekly_activity = db.relationship('WeeklyActivity', back_populates='daily_entries')

    def __repr__(self):
        return f"<DailyActivity {self.day_of_week} ({self.date}) [Week #{self.weekly_activity_id}]>"
