"""Idempotently adds the HW7 username and role columns to users."""
from sqlalchemy import inspect, text

from database import db_session_basede26


def migrate() -> None:
    inspector = inspect(db_session_basede26)
    columns = {column["name"] for column in inspector.get_columns("users")}
    with db_session_basede26.begin() as connection:
        if "username" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(100) NULL"))
        if "role" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'reader'"))
        connection.execute(text("UPDATE users SET username = email WHERE username IS NULL"))
        connection.execute(text("UPDATE users SET role = 'reader' WHERE role IS NULL OR role = ''"))
        try:
            connection.execute(text("ALTER TABLE users ADD CONSTRAINT uq_users_username UNIQUE (username)"))
        except Exception as error:  # existing constraint is the idempotent case
            if "already exists" not in str(error).lower() and "duplicate" not in str(error).lower():
                raise
    print("HW7 users migration PASS")


if __name__ == "__main__":
    migrate()
