import os
from app import create_app
from app.extensions import db
from app.utils.seed_data import seed_database

app = create_app(os.getenv('FLASK_ENV', 'production'))

# Auto-initialize and seed database upon Gunicorn startup (e.g. Render deployments)
with app.app_context():
    try:
        db.create_all()
        seed_database()
    except Exception as e:
        app.logger.warning(f"WSGI auto-initialization notice: {e}")

if __name__ == '__main__':
    app.run()

