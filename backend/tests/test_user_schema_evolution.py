from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from unifoli_api.core import database as database_module


def test_apply_schema_evolution_adds_marketing_agreed_to_legacy_users_table(tmp_path, monkeypatch) -> None:
    legacy_db_path = tmp_path / "legacy-users.db"
    legacy_engine = create_engine(f"sqlite:///{legacy_db_path.as_posix()}", future=True)

    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id VARCHAR(36) PRIMARY KEY,
                    firebase_uid VARCHAR(128) NOT NULL,
                    email VARCHAR(255),
                    name VARCHAR(200),
                    target_university VARCHAR(200),
                    target_major VARCHAR(200),
                    grade VARCHAR(50),
                    track VARCHAR(100),
                    career VARCHAR(200),
                    admission_type VARCHAR(100),
                    interest_universities JSON,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )

    monkeypatch.setattr(database_module, "engine", legacy_engine)
    monkeypatch.setattr(
        database_module,
        "SessionLocal",
        sessionmaker(bind=legacy_engine, autoflush=False, autocommit=False, expire_on_commit=False),
    )

    database_module._apply_schema_evolution()

    users_columns = {column["name"] for column in inspect(legacy_engine).get_columns("users")}
    assert "marketing_agreed" in users_columns

    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (id, firebase_uid, created_at, updated_at)
                VALUES ('legacy-user-1', 'legacy:uid:1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        marketing_agreed = connection.execute(
            text("SELECT marketing_agreed FROM users WHERE id = 'legacy-user-1'")
        ).scalar_one()

    assert marketing_agreed in (0, False)

