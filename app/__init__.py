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

    # Initialize storage service
    app.storage_service = LocalStorageService(app.config['UPLOAD_FOLDER'])

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.student import student_bp
    from app.routes.liaison import liaison_bp
    from app.routes.supervisor import supervisor_bp
    from app.routes.admin import admin_bp
    from app.routes.api_v1 import api_v1_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(liaison_bp, url_prefix='/liaison')
    app.register_blueprint(supervisor_bp, url_prefix='/supervisor')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')

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

    @app.cli.command('seed-db')
    def seed_db_command():
        """Seeds demo data into existing database."""
        from app.utils.seed_data import seed_database
        with app.app_context():
            seed_database()

    return app
