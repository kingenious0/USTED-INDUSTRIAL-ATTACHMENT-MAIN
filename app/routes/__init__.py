from app.routes.auth import auth_bp
from app.routes.main import main_bp
from app.routes.student import student_bp
from app.routes.liaison import liaison_bp
from app.routes.supervisor import supervisor_bp
from app.routes.admin import admin_bp
from app.routes.api_v1 import api_v1_bp

__all__ = [
    'auth_bp',
    'main_bp',
    'student_bp',
    'liaison_bp',
    'supervisor_bp',
    'admin_bp',
    'api_v1_bp'
]
