from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, current_app, jsonify, request
from flask_login import current_user
from app.routes.auth import redirect_by_role

main_bp = Blueprint('main', __name__)


@main_bp.app_context_processor
def inject_global_vars():
    """Injects university name, current year, and settings into all Jinja templates."""
    return {
        'current_year': datetime.now().year,
        'university_name': current_app.config.get(
            'UNIVERSITY_NAME', 
            'University of Skills Training and Entrepreneurial Development (USTED)'
        ),
        'liaison_unit_name': 'Industrial Liaison Office',
        'app_version': '3.0.0'
    }


@main_bp.route('/')
def index():
    if current_user.is_authenticated and not request.args.get('landing'):
        return redirect_by_role(current_user)
    return render_template('index.html')


@main_bp.route('/portal/access/<path:index_number>')
def portal_access(index_number: str):
    """Direct root gateway for physical Introductory Letter QR codes (PRD 3.0)."""
    return redirect(url_for('auth.portal_access', index_number=index_number, token=request.args.get('token')))


@main_bp.route('/switch-role/<role>')
def switch_role(role: str):
    return redirect(url_for('auth.switch_role', role=role, next=request.args.get('next')))


@main_bp.route('/health')
def health_check():
    """System health endpoint for hosting platforms like Render."""
    return jsonify({
        'status': 'healthy',
        'system': 'USTED Industrial Attachment Management System (U-IAP)',
        'version': '3.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200
