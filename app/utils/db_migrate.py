import logging
from sqlalchemy import text
from app.extensions import db

logger = logging.getLogger(__name__)


def migrate_database_schema(app=None):
    """
    Idempotent schema upgrade for existing SQLite / PostgreSQL databases.
    Safely creates missing tables and adds missing columns without data loss.
    """
    def _execute():
        # 1. Ensure all new tables exist (e.g. supervision_visits)
        db.create_all()

        # 2. Inspect acceptance_records columns
        try:
            engine = db.engine
            dialect_name = engine.dialect.name

            if dialect_name == 'sqlite':
                with engine.connect() as conn:
                    result = conn.execute(text("PRAGMA table_info(acceptance_records)"))
                    existing_cols = {row[1] for row in result.fetchall()}

                    columns_to_add = [
                        ('region', 'VARCHAR(100)'),
                        ('district_town', 'VARCHAR(150)'),
                        ('gps_address', 'VARCHAR(50)'),
                        ('landmark', 'VARCHAR(255)'),
                        ('latitude', 'FLOAT'),
                        ('longitude', 'FLOAT')
                    ]

                    for col_name, col_type in columns_to_add:
                        if col_name not in existing_cols:
                            logger.info(f"Adding missing column {col_name} to acceptance_records...")
                            conn.execute(text(f"ALTER TABLE acceptance_records ADD COLUMN {col_name} {col_type}"))

                    # Inspect users columns
                    result_users = conn.execute(text("PRAGMA table_info(users)"))
                    existing_user_cols = {row[1] for row in result_users.fetchall()}
                    user_cols_to_add = [
                        ('phone', 'VARCHAR(50)'),
                        ('office_location', 'VARCHAR(255)'),
                        ('avatar_path', 'VARCHAR(255)'),
                        ('staff_id', 'VARCHAR(50)'),
                        ('department', 'VARCHAR(150)'),
                        ('display_title', 'VARCHAR(50)'),
                        ('account_status', "VARCHAR(20) NOT NULL DEFAULT 'active'"),
                        ('is_first_login', 'BOOLEAN NOT NULL DEFAULT 0'),
                        ('temp_password_hash', 'VARCHAR(255)'),
                        ('provisioned_by_id', 'INTEGER'),
                        ('provisioned_at', 'DATETIME'),
                        ('student_master_id', 'INTEGER'),
                    ]
                    for col_name, col_type in user_cols_to_add:
                        if col_name not in existing_user_cols:
                            logger.info(f"Adding missing column {col_name} to users...")
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))

                    conn.commit()

            elif dialect_name in ('postgresql', 'postgres'):
                with engine.connect() as conn:
                    columns_to_add = [
                        ('region', 'VARCHAR(100)'),
                        ('district_town', 'VARCHAR(150)'),
                        ('gps_address', 'VARCHAR(50)'),
                        ('landmark', 'VARCHAR(255)'),
                        ('latitude', 'DOUBLE PRECISION'),
                        ('longitude', 'DOUBLE PRECISION')
                    ]
                    for col_name, col_type in columns_to_add:
                        conn.execute(text(f"ALTER TABLE acceptance_records ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))

                    user_cols_to_add = [
                        ('phone', 'VARCHAR(50)'),
                        ('office_location', 'VARCHAR(255)'),
                        ('avatar_path', 'VARCHAR(255)'),
                        ('staff_id', 'VARCHAR(50)'),
                        ('department', 'VARCHAR(150)'),
                        ('display_title', 'VARCHAR(50)'),
                        ('account_status', "VARCHAR(20) NOT NULL DEFAULT 'active'"),
                        ('is_first_login', 'BOOLEAN NOT NULL DEFAULT FALSE'),
                        ('temp_password_hash', 'VARCHAR(255)'),
                        ('provisioned_by_id', 'INTEGER'),
                        ('provisioned_at', 'TIMESTAMP WITH TIME ZONE'),
                        ('student_master_id', 'INTEGER'),
                    ]
                    for col_name, col_type in user_cols_to_add:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))

                    conn.commit()

        except Exception as e:
            logger.warning(f"Schema auto-migration notice: {e}")

    if app:
        with app.app_context():
            _execute()
    else:
        _execute()
