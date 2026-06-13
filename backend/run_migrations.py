import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Set it to your PostgreSQL connection string.")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def main():
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("No migrations found.")
        return

    with psycopg.connect(DATABASE_URL) as connection:
        for migration_file in migration_files:
            sql = migration_file.read_text(encoding="utf-8")
            print(f"Running {migration_file.name}")
            connection.execute(sql)

    print("Migrations complete.")


if __name__ == "__main__":
    main()
