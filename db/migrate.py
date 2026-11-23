"""Apply pending numbered migrations (db/NNN_*.sql) and record them in schema_migrations.

Usage (from anywhere; reads DATABASE_URL from local.env in the repo root):
    python db/migrate.py              # apply all pending migrations
    python db/migrate.py --status     # list applied / pending migrations, change nothing
    python db/migrate.py --baseline 006
        # mark 001-006 as applied WITHOUT running them (for a database that
        # already had those migrations applied by hand before tracking existed)

Each migration runs in its own transaction together with its schema_migrations
insert, so a failing migration leaves nothing half-applied.

Rules:
    - Never edit a migration that has been applied anywhere; add a new numbered file.
    - Migration files must be plain SQL (no psql meta-commands like \\c).
"""

import argparse
import os
import re
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

DB_DIR = Path(__file__).resolve().parent
REPO_ROOT = DB_DIR.parent
MIGRATION_RE = re.compile(r"^(\d{3})_.+\.sql$")

CREATE_TRACKING_TABLE = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version    VARCHAR(3) PRIMARY KEY,
        filename   TEXT NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
"""


def find_migrations():
    """Return [(version, path)] sorted by version; error on duplicate numbers."""
    migrations = {}
    for path in sorted(DB_DIR.glob("*.sql")):
        match = MIGRATION_RE.match(path.name)
        if not match:
            continue
        version = match.group(1)
        if version in migrations:
            sys.exit(
                f"Duplicate migration number {version}: "
                f"{migrations[version].name} and {path.name}. Renumber one of them."
            )
        migrations[version] = path
    return sorted(migrations.items())


def applied_versions(cur):
    cur.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def table_exists(cur, name):
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{name}",))
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true", help="show applied/pending migrations only")
    group.add_argument("--baseline", metavar="VERSION", help="mark migrations up to VERSION as applied without running them")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / "local.env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL is not set (expected in local.env).")

    migrations = find_migrations()

    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(CREATE_TRACKING_TABLE)
            done = applied_versions(cur)

        pending = [(v, p) for v, p in migrations if v not in done]

        if args.status:
            for version, path in migrations:
                print(f"  [{'x' if version in done else ' '}] {path.name}")
            unknown = done - {v for v, _ in migrations}
            for version in sorted(unknown):
                print(f"  [?] {version} recorded as applied but no file found on this branch")
            print(f"{len(pending)} pending.")
            return

        if args.baseline:
            target = args.baseline.zfill(3)
            to_mark = [(v, p) for v, p in pending if v <= target]
            with conn, conn.cursor() as cur:
                for version, path in to_mark:
                    cur.execute(
                        "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                        (version, path.name),
                    )
                    print(f"Marked as applied (not run): {path.name}")
            print(f"Baselined {len(to_mark)} migration(s).")
            return

        # Guard: an untracked database that already has tables almost certainly
        # had migrations applied by hand. Running 001 again would be wrong.
        if not done:
            with conn, conn.cursor() as cur:
                if table_exists(cur, "solar_production"):
                    sys.exit(
                        "schema_migrations is empty but tables already exist.\n"
                        "Record what's already applied first, e.g.:\n"
                        "    python db/migrate.py --baseline 006"
                    )

        if not pending:
            print("Database is up to date.")
            return

        for version, path in pending:
            sql = path.read_text(encoding="utf-8")
            print(f"Applying {path.name} ...", end=" ", flush=True)
            try:
                with conn, conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                        (version, path.name),
                    )
            except psycopg2.Error as exc:
                print("FAILED")
                sys.exit(f"{path.name} was rolled back; later migrations were not run.\n{exc}")
            print("ok")
        print(f"Applied {len(pending)} migration(s).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
