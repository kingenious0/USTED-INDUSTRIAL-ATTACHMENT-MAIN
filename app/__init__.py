import os
from flask import Flask, render_template
from app.config import config_by_name
from app.extensions import db, login_manager, csrf, migrate
from app.models.user import User
from app.services.storage import LocalStorageService


def create_app(config_name: str = None) -> Flask:
    """Application factory for U-IAP Core System."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Global Hook: Enable instantaneous role switching via ?role=student/liaison/admin/supervisor
    from flask import request
    from flask_login import login_user

    @app.before_request
    def handle_global_role_preview():
        role_param = request.args.get('role')
        if role_param:
            role_map = {
                'student': '5230100452',
                'liaison': 'liaison1',
                'liaison_officer': 'liaison1',
                'admin': 'admin1',
                'liaison_head': 'admin1',
                'supervisor': 'supervisor1',
                'academic_supervisor': 'supervisor1'
            }
            username = role_map.get(role_param.lower().strip())
            if username:
                try:
                    user = User.query.filter_by(username=username).first()
                    if not user and not app.config.get('TESTING'):
                        db.create_all()
                        from app.utils.seed_data import seed_database
                        seed_database()
                        user = User.query.filter_by(username=username).first()
                    if user:
                        login_user(user)
                except Exception:
                    db.session.rollback()
                    if not app.config.get('TESTING'):
                        try:
                            db.create_all()
                            from app.utils.seed_data import seed_database
                            seed_database()
                            user = User.query.filter_by(username=username).first()
                            if user:
                                login_user(user)
                        except Exception:
                            pass

    # Initialize storage service
    app.storage_service = LocalStorageService(app.config['UPLOAD_FOLDER'])

    # Jinja Template Filter: Format Audit Details as Human-Readable Text
    @app.template_filter('humanize_audit')
    def humanize_audit_filter(log):
        if not log:
            return "—"
        action = getattr(log, 'action', '') or ""
        details = getattr(log, 'details', {}) or {}
        ip = getattr(log, 'ip_address', '') or 'Localhost'
        
        if action == 'USER_LOGIN':
            role = (getattr(log, 'actor_role', '') or details.get('role', 'User')).replace('_', ' ').title()
            return f"User Logged In ({role}) from {ip}"
        elif action == 'USER_LOGOUT':
            return f"User Logged Out ({ip})"
        elif action == 'STUDENT_LOOKUP':
            query = details.get('query', '')
            count = details.get('results_count', 0)
            return f"Looked up student \"{query}\" ({count} record{'s' if count != 1 else ''} found)"
        elif action == 'ATTACHMENT_INITIATED':
            weeks = details.get('duration_weeks', '')
            year = details.get('academic_year', '')
            return f"Initiated {weeks}-week attachment ({year})"
        elif action == 'LETTER_GENERATED':
            ref = details.get('reference_number', '')
            org = details.get('target_organization', '')
            return f"Generated Introductory Letter ({ref}) for {org}" if org else f"Generated Introductory Letter ({ref})"
        elif action == 'LETTER_REPRINTED':
            reason = details.get('reason', 'Replacement requested')
            org = details.get('target_organization', '')
            return f"Reprinted letter for {org} — Reason: {reason}" if org else f"Reprinted letter — Reason: {reason}"
        elif action == 'ACCEPTANCE_UPLOADED':
            org = details.get('organization_name', '')
            loc = details.get('location', '')
            return f"Uploaded Acceptance Form: {org} ({loc})" if loc else f"Uploaded Acceptance Form: {org}"
        elif action == 'ACCEPTANCE_REVIEWED':
            decision = (details.get('decision') or details.get('status') or '').replace('_', ' ').title()
            notes = details.get('notes', '')
            if notes:
                return f"Review Decision: {decision} — Note: {notes}"
            return f"Review Decision: {decision}" if decision else "Acceptance Form reviewed"
        elif action == 'WEEK_LOCKED':
            num = details.get('week_number', '')
            return f"Locked Week {num} daily activity logbook"
        elif action == 'WEEK_UNLOCKED':
            num = details.get('week_number', '')
            return f"Unlocked Week {num} daily activity logbook"
        elif action == 'CONFIG_CHANGED':
            key = details.get('key', 'Policy')
            val = details.get('value', '')
            return f"Updated policy setting: {key} = {val}"
        
        if isinstance(details, dict) and details:
            parts = [f"{k.replace('_', ' ').title()}: {v}" for k, v in details.items() if v is not None]
            return " | ".join(parts) if parts else "—"
        return getattr(log, 'details_json', '') or "—"


    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.student import student_bp
    from app.routes.liaison import liaison_bp
    from app.routes.supervisor import supervisor_bp
    from app.routes.admin import admin_bp
    from app.routes.api_v1 import api_v1_bp
    from app.activities import activities_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(liaison_bp, url_prefix='/liaison')
    app.register_blueprint(supervisor_bp, url_prefix='/supervisor')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    app.register_blueprint(activities_bp, url_prefix='/activities')

    # Register Error Handlers
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return render_template(
            'errors/403.html',
            custom_title="File Too Large",
            custom_message="The uploaded file exceeds the 10 MB maximum permitted upload size."
        ), 413

    # CLI commands for easy management
    @app.cli.command('init-db')
    def init_db_command():
        """Creates database tables and seeds demo data."""
        from app.utils.seed_data import seed_database
        with app.app_context():
            db.create_all()
            seed_database()
            print("Database initialized successfully.")

    # Auto-initialize database tables and seed data in non-testing environments (e.g. Render / Gunicorn)
    if not app.config.get('TESTING'):
        with app.app_context():
            try:
                db.create_all()
                from app.utils.seed_data import seed_database
                seed_database()
            except Exception as e:
                app.logger.warning(f"Database auto-bootstrap notice: {e}")

    return app
