"""
Thin MySQL connection helper. Reads from the SAME database the PHP app
uses (see app/config.py). This service should primarily READ from
`users` and `assessments`, and READ/WRITE `training_programs` and
`training_recommendations`.
"""
import mysql.connector
from mysql.connector import MySQLConnection

from app.config import settings


def get_connection() -> MySQLConnection:
    # charset/use_unicode must be explicit: without them, mysql-connector
    # has been observed round-tripping UTF-8 multi-byte characters (e.g.
    # em dashes in scripts/seed_training_programs.py) through a Latin-1/
    # cp1252 misinterpretation, corrupting them into mojibake on INSERT
    # (e.g. "—" becoming three separate wrong characters). See
    # scripts/fix_mojibake.py if you find more corrupted rows later.
    return mysql.connector.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        use_unicode=True,
    )


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        conn.close()


def execute(query: str, params: tuple = ()) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
    finally:
        conn.close()

