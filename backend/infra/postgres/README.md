# Postgres Infra

Primary database for transactional data plus vector search through pgvector.

## Owns

- schema migrations
- extensions
- backup policy
- row-level access strategy

## Local Notes

- `docker-compose.yml` uses a pgvector-enabled Postgres image.
- `init/01-init-db.sql` creates the `vector` extension on first container boot.
- The backend still supports SQLite for local development, but Postgres remains the deployment posture for durable environments.

## Deployment Posture

- Treat Alembic as the source of truth for schema creation and evolution.
- Run `alembic upgrade head` before the API or worker starts serving traffic.
- Local/test startup may auto-apply migrations for convenience, but deployed runtimes should not depend on `create_all()` or manual `ALTER TABLE` repair as a success path.
- When pgvector is enabled, keep the extension installation step in place before running migrations that create vector-backed indexes.
