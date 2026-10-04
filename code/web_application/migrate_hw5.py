"""Idempotent HW5 migration from the HW4 clinical-trials schema."""

from sqlalchemy import inspect, text

from database import db_session_basede26


def table_names():
    return set(inspect(db_session_basede26).get_table_names())


def column_names(table_name):
    return {
        column["name"]
        for column in inspect(db_session_basede26).get_columns(table_name)
    }


def constraint_names(table_name):
    inspector = inspect(db_session_basede26)
    names = {
        item.get("name")
        for item in inspector.get_unique_constraints(table_name)
    }
    names.update(
        item.get("name")
        for item in inspector.get_foreign_keys(table_name)
    )
    return names


def execute(sql, parameters=None):
    with db_session_basede26.begin() as connection:
        connection.execute(text(sql), parameters or {})


def scalar(sql):
    with db_session_basede26.connect() as connection:
        return connection.execute(text(sql)).scalar()


def migrate():
    print("HW5 migration starting")

    if "sponsors" not in table_names():
        execute(
            """
            CREATE TABLE sponsors (
                id INT NOT NULL AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL,
                contact_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                CONSTRAINT uq_sponsors_email UNIQUE (email)
            ) ENGINE=InnoDB
            """
        )
        print("Created sponsors table")

    trial_columns = column_names("trials")

    if "sponsor" in trial_columns and scalar("SELECT COUNT(*) FROM sponsors") == 0:
        with db_session_basede26.connect() as connection:
            names = connection.execute(
                text("SELECT DISTINCT sponsor FROM trials ORDER BY sponsor")
            ).scalars().all()

        with db_session_basede26.begin() as connection:
            for index, name in enumerate(names, start=1):
                connection.execute(
                    text(
                        """
                        INSERT INTO sponsors (name, contact_name, email)
                        VALUES (:name, :contact_name, :email)
                        """
                    ),
                    {
                        "name": name,
                        "contact_name": f"Contact for {name}",
                        "email": f"sponsor{index:03d}@example.edu",
                    },
                )
        print(f"Migrated {len(names)} sponsors")

    additions = {
        "nct_code": "VARCHAR(11) NULL",
        "participant_count": "INT NOT NULL DEFAULT 0",
        "sponsor_id": "INT NULL",
        "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "updated_at": (
            "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP "
            "ON UPDATE CURRENT_TIMESTAMP"
        ),
    }

    for column_name, definition in additions.items():
        if column_name not in column_names("trials"):
            execute(
                f"ALTER TABLE trials ADD COLUMN {column_name} {definition}"
            )
            print(f"Added trials.{column_name}")

    execute(
        """
        UPDATE trials
        SET nct_code = CONCAT('NCT', LPAD(id, 8, '0'))
        WHERE nct_code IS NULL
        """
    )

    if "sponsor" in column_names("trials"):
        execute(
            """
            UPDATE trials AS trial
            JOIN sponsors AS sponsor
              ON sponsor.name = trial.sponsor
            SET trial.sponsor_id = sponsor.id
            WHERE trial.sponsor_id IS NULL
            """
        )

    missing_codes = scalar(
        "SELECT COUNT(*) FROM trials WHERE nct_code IS NULL"
    )
    missing_sponsors = scalar(
        "SELECT COUNT(*) FROM trials WHERE sponsor_id IS NULL"
    )

    if missing_codes or missing_sponsors:
        raise RuntimeError(
            "Migration validation failed: "
            f"missing_codes={missing_codes}, "
            f"missing_sponsors={missing_sponsors}"
        )

    execute("ALTER TABLE trials MODIFY nct_code VARCHAR(11) NOT NULL")
    execute("ALTER TABLE trials MODIFY sponsor_id INT NOT NULL")

    constraints = constraint_names("trials")

    if "uq_trials_nct_code" not in constraints:
        execute(
            """
            ALTER TABLE trials
            ADD CONSTRAINT uq_trials_nct_code UNIQUE (nct_code)
            """
        )
        print("Added unique NCT-code constraint")

    constraints = constraint_names("trials")

    if "fk_trials_sponsor_id" not in constraints:
        execute(
            """
            ALTER TABLE trials
            ADD CONSTRAINT fk_trials_sponsor_id
            FOREIGN KEY (sponsor_id) REFERENCES sponsors(id)
            ON DELETE RESTRICT
            """
        )
        print("Added Sponsor-Trial foreign key")

    if "sponsor" in column_names("trials"):
        execute("ALTER TABLE trials DROP COLUMN sponsor")
        print("Removed legacy trials.sponsor text column")

    sponsor_count = scalar("SELECT COUNT(*) FROM sponsors")
    trial_count = scalar("SELECT COUNT(*) FROM trials")
    linked_count = scalar(
        "SELECT COUNT(*) FROM trials WHERE sponsor_id IS NOT NULL"
    )

    print(f"sponsors={sponsor_count}")
    print(f"trials={trial_count}")
    print(f"linked_trials={linked_count}")
    print("HW5 migration PASS")


if __name__ == "__main__":
    migrate()
