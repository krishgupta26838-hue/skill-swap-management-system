"""
reset_db.py
Command-line utility to instantly reboot/reset the SkillSwap MySQL database
back to the clean, original seed state.

Usage:
    .\\.venv\\Scripts\\python.exe reset_db.py
"""

import os
import mysql.connector
from dotenv import load_dotenv
from app import split_sql_statements

def reset_database():
    load_dotenv()
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "skill_swap_db")

    print(f"Connecting to MySQL ({host}) as '{user}'...")
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        buffered=True
    )
    cursor = conn.cursor(buffered=True)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Read and apply schema.sql
    schema_path = os.path.join(base_dir, "schema.sql")
    print(f"Applying schema from '{schema_path}'...")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_content = f.read()

    schema_stmts = split_sql_statements(schema_content)
    for stmt in schema_stmts:
        cursor.execute(stmt)
        if cursor.with_rows:
            cursor.fetchall()

    # Read and apply seed.sql
    seed_path = os.path.join(base_dir, "seed.sql")
    print(f"Applying seed data from '{seed_path}'...")
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_content = f.read()

    seed_stmts = split_sql_statements(seed_content)
    for stmt in seed_stmts:
        cursor.execute(stmt)
        if cursor.with_rows:
            cursor.fetchall()

    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ SUCCESS: Database 'skill_swap_db' has been completely rebooted to initial seed state!")

if __name__ == "__main__":
    reset_database()
