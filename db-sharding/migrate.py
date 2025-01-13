import os
import psycopg2


def run_migration(db_config, sql_script):
    """Run SQL script against the specified database."""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        with open(sql_script, "r") as f:
            cursor.execute(f.read())
        conn.commit()
        print(f"Migration for {db_config['dbname']} complete.")
    except Exception as e:
        print(f"Error migrating {db_config['dbname']}: {e}")
    finally:
        if conn:
            assert cursor is not None, f"Cursor can't be None for {conn=}."
            cursor.close()
            conn.close()


# Database configurations
databases = [
    {
        "host": os.getenv("DB_1_URL", "db-1"),
        "port": 5432,
        "dbname": "shard1",
        "user": "user1",
        "password": "password1",
    },
    {
        "host": os.getenv("DB_2_URL", "db-2"),
        "port": 5432,
        "dbname": "shard2",
        "user": "user2",
        "password": "password2",
    },
    {
        "host": os.getenv("DB_3_URL", "db-3"),
        "port": 5432,
        "dbname": "shard3",
        "user": "user3",
        "password": "password3",
    },
]

# Run migration for each database
sql_script_path = os.path.join(os.path.dirname(__file__), "init.sql")
for db_config in databases:
    run_migration(db_config, sql_script_path)
