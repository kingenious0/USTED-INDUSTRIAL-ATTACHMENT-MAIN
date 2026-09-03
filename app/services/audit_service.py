from flask import request, has_request_context
from flask_login import current_user
from app.extensions import db
from app.models.audit import AuditLog


class AuditService:
    @staticmethod
    def log(
        action: str,
        target_type: str = None,
        target_id: int = None,
        details: dict = None,
        actor=None
    ) -> AuditLog:
        """
        Record a structured audit log entry adhering to PRD Section 31.
        Automatically extracts IP address, user agent, and authenticated user if in request context.
        """
        ip_address = None
        user_agent = None

        if has_request_context():
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address and ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()
            user_agent = request.user_agent.string if request.user_agent else None

        actor_user = actor
        if actor_user is None and has_request_context() and current_user and current_user.is_authenticated:
            actor_user = current_user

        actor_id = actor_user.id if actor_user else None
        actor_username = actor_user.username if actor_user else 'SYSTEM'
        actor_role = actor_user.role if actor_user else 'system'

        log_entry = AuditLog(
            actor_id=actor_id,
            actor_username=actor_username,
            actor_role=actor_role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        if details:
            log_entry.details = details

        db.session.add(log_entry)
        db.session.commit()
        return log_entry
