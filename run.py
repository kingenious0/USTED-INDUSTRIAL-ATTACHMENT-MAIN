import os
from app import create_app

app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Automatically initialize and seed SQLite db in local development if needed
    with app.app_context():
        from app.utils.db_migrate import migrate_database_schema
        from app.utils.seed_data import seed_database
        migrate_database_schema()
        seed_database()

    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
