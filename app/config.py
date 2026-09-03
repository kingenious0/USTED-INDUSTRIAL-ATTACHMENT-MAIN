import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-u-iap-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database
    _raw_db_uri = os.getenv('DATABASE_URL', f"sqlite:///{BASE_DIR / 'u_iap.db'}")
    if _raw_db_uri and _raw_db_uri.startswith('postgres://'):
        _raw_db_uri = _raw_db_uri.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _raw_db_uri
    
    # File Uploads & Storage
    STORAGE_PROVIDER = os.getenv('STORAGE_PROVIDER', 'local')
    UPLOAD_FOLDER = BASE_DIR / os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))  # 10 MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'image/png',
        'image/jpeg',
        'image/pjpeg'
    }

    # Operational Workflow Configuration (PRD OQ-04)
    # When True: Logging locked until Liaison approves Acceptance Form
    # When False: Logging enabled immediately; review occurs asynchronously
    REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING = os.getenv(
        'REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING', 'false'
    ).lower() in ('true', '1', 't', 'yes')

    # University & Liaison Signatory Information (PRD 3.0)
    UNIVERSITY_NAME = os.getenv(
        'UNIVERSITY_NAME', 
        'University of Skills Training and Entrepreneurial Development (USTED)'
    )
    LIAISON_HEAD_NAME = os.getenv('LIAISON_HEAD_NAME', 'DONALD KWAME ASIEDU (ChPA)')
    LIAISON_HEAD_TITLE = os.getenv('LIAISON_HEAD_TITLE', 'Head, Industrial Liaison Office')
    
    # External Decoupled eLogBook SSO
    EXTERNAL_ELOGBOOK_URL = os.getenv('EXTERNAL_ELOGBOOK_URL', 'https://usted-elogbook.vercel.app')


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = BASE_DIR / 'test_uploads'


class ProductionConfig(Config):
    DEBUG = False
    # Enforce secure cookies in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
