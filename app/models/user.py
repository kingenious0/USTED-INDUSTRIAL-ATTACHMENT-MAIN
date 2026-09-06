from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class UserRole:
    STUDENT = 'student'
    LIAISON_SECRETARY = 'liaison_secretary'
    LIAISON_OFFICER = 'liaison_officer'
    LIAISON_HEAD = 'liaison_head'
    ACADEMIC_SUPERVISOR = 'academic_supervisor'
    DEPARTMENT_EVALUATOR = 'department_evaluator'
    SYSTEM_ADMIN = 'system_admin'

    ALL_ROLES = [
        STUDENT,
        LIAISON_SECRETARY,
        LIAISON_OFFICER,
        LIAISON_HEAD,
        ACADEMIC_SUPERVISOR,
        DEPARTMENT_EVALUATOR,
        SYSTEM_ADMIN,
    ]

    # Roles that can access provisioning console
    ADMIN_ROLES = [LIAISON_HEAD, SYSTEM_ADMIN]

    # Provisionable (non-student) roles
    STAFF_ROLES = [LIAISON_SECRETARY, LIAISON_OFFICER, LIAISON_HEAD, ACADEMIC_SUPERVISOR, DEPARTMENT_EVALUATOR, SYSTEM_ADMIN]

    # Human-readable labels
    LABELS = {
        STUDENT: 'Student',
        LIAISON_SECRETARY: 'Liaison Secretary',
        LIAISON_OFFICER: 'Liaison Officer',
        LIAISON_HEAD: 'Liaison Head',
        ACADEMIC_SUPERVISOR: 'Academic Supervisor',
        DEPARTMENT_EVALUATOR: 'Department Evaluator',
        SYSTEM_ADMIN: 'System Administrator',
    }


class AccountStatus:
    ACTIVE = 'active'
    PENDING_CLAIM = 'pending_claim'
    SUSPENDED = 'suspended'


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

    # Profile particulars & institutional governance
    phone = db.Column(db.String(50), nullable=True)
    office_location = db.Column(db.String(255), nullable=True)
    avatar_path = db.Column(db.String(255), nullable=True)
    staff_id = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(150), nullable=True)
    display_title = db.Column(db.String(50), nullable=True)  # e.g. "Ing. Dr.", "Prof.", "Mr."

    # --- Provisioning & First-Login Claim fields ---
    account_status = db.Column(db.String(20), nullable=False, default=AccountStatus.ACTIVE)
    is_first_login = db.Column(db.Boolean, default=False, nullable=False)
    temp_password_hash = db.Column(db.String(255), nullable=True)   # cleared after claim
    provisioned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    provisioned_at = db.Column(db.DateTime, nullable=True)

    # Provisioner relationship (self-referential)
    provisioned_by = db.relationship(
        'User', remote_side=[id], foreign_keys=[provisioned_by_id],
        backref=db.backref('provisioned_users', lazy='dynamic')
    )

    # Optional 1:1 linkage to student master record if role is student
    student_master_id = db.Column(db.Integer, db.ForeignKey('student_masters.id'), nullable=True)
    student_master = db.relationship('StudentMaster', backref=db.backref('user', uselist=False))

    # ------------------------------------------------------------------
    # Password helpers
    # ------------------------------------------------------------------
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def set_temp_password(self, temp_password: str):
        """Stores a temporary credential hash for first-login provisioning."""
        self.temp_password_hash = generate_password_hash(temp_password)

    def check_temp_password(self, temp_password: str) -> bool:
        """Verifies temp credential; only valid while is_first_login is True."""
        if not self.temp_password_hash:
            return False
        return check_password_hash(self.temp_password_hash, temp_password)

    # ------------------------------------------------------------------
    # Role helpers
    # ------------------------------------------------------------------
    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_liaison(self):
        return self.role in (UserRole.LIAISON_SECRETARY, UserRole.LIAISON_OFFICER, UserRole.LIAISON_HEAD)

    @property
    def is_admin(self):
        return self.role in UserRole.ADMIN_ROLES

    @property
    def is_supervisor(self):
        return self.role == UserRole.ACADEMIC_SUPERVISOR

    @property
    def role_label(self) -> str:
        return UserRole.LABELS.get(self.role, self.role.replace('_', ' ').title())

    @property
    def status_label(self) -> str:
        labels = {
            AccountStatus.ACTIVE: 'Active',
            AccountStatus.PENDING_CLAIM: 'Pending Claim',
            AccountStatus.SUSPENDED: 'Suspended',
        }
        return labels.get(self.account_status, self.account_status.title())

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    @property
    def initials(self) -> str:
        """Derives clean 2-letter uppercase initials ignoring academic / honorific titles."""
        if not self.full_name:
            return "U"
        import re
        cleaned = re.sub(r'\([^)]*\)', '', self.full_name)
        cleaned = re.sub(r'\b(Ing|Dr|Prof|Rev|Mrs|Mr|Ms|Miss|Esq)\b\.?', '', cleaned, flags=re.IGNORECASE)
        parts = [p.strip() for p in cleaned.split() if p.strip()]
        if not parts:
            parts = [p.strip() for p in self.full_name.split() if p.strip()]
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif len(parts) == 1 and len(parts[0]) >= 2:
            return parts[0][:2].upper()
        elif len(parts) == 1:
            return parts[0][0].upper()
        return "U"

    @property
    def display_name(self) -> str:
        """Full name with optional title prefix."""
        if self.display_title:
            return f"{self.display_title} {self.full_name}"
        return self.full_name

    @property
    def display_phone(self) -> str:
        """Resolves active contact phone across user and student master records."""
        if self.phone:
            return self.phone
        if self.student_master and self.student_master.phone:
            return self.student_master.phone
        return ""

    @property
    def display_staff_id(self) -> str:
        """Resolves institutional index or staff ID."""
        if self.student_master and self.student_master.index_number:
            return self.student_master.index_number
        if self.staff_id:
            return self.staff_id
        if self.is_supervisor:
            return f"USTED-FAC-014{self.id}"
        if self.is_liaison:
            return f"USTED-LIA-001{self.id}"
        return f"USTED-ADM-00{self.id}"

    @property
    def display_department(self) -> str:
        """Resolves assigned faculty or directorate."""
        if self.student_master:
            return self.student_master.department or self.student_master.programme or "Information Technology Education"
        if self.department:
            return self.department
        if self.is_supervisor:
            return "Information Technology Education"
        if self.is_liaison:
            return "Industrial Liaison Directorate"
        return "Directorate of Academic Practicum & WEL"

    @property
    def avatar_url(self) -> str:
        """Returns web-accessible path for uploaded avatar or None."""
        if self.avatar_path:
            return f"/static/uploads/avatars/{self.avatar_path}"
        return ""

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"
