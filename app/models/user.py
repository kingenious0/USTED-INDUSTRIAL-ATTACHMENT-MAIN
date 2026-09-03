from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class UserRole:
    STUDENT = 'student'
    LIAISON_OFFICER = 'liaison_officer'
    LIAISON_HEAD = 'liaison_head'
    ACADEMIC_SUPERVISOR = 'academic_supervisor'
    DEPARTMENT_EVALUATOR = 'department_evaluator'
    
    ALL_ROLES = [
        STUDENT,
        LIAISON_OFFICER,
        LIAISON_HEAD,
        ACADEMIC_SUPERVISOR,
        DEPARTMENT_EVALUATOR
    ]


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default=UserRole.STUDENT, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Optional 1:1 linkage to student master record if role is student
    student_master_id = db.Column(db.Integer, db.ForeignKey('student_masters.id'), nullable=True)
    student_master = db.relationship('StudentMaster', backref=db.backref('user', uselist=False))

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_liaison(self):
        return self.role in (UserRole.LIAISON_OFFICER, UserRole.LIAISON_HEAD)

    @property
    def is_admin(self):
        return self.role == UserRole.LIAISON_HEAD

    @property
    def is_supervisor(self):
        return self.role == UserRole.ACADEMIC_SUPERVISOR

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"
