
import os
import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import RealDictCursor


load_dotenv()


class DatabaseUtil:
    """Utility class for PostgreSQL schema inspection and read-only queries."""

    def __init__(self, db_config):
        self.db_config = db_config
        self.connection = None

        try:
            self.connection = psycopg2.connect(**db_config)
            self.connection.autocommit = False
        except psycopg2.Error as e:
            print(f"Error connecting to the database: {e}")
            self.connection = None

    def _get_connection(self):
        """Return a valid database connection or raise an error."""
        if self.connection is None or self.connection.closed:
            raise ConnectionError(
                "Database connection is unavailable. Check PostgreSQL and .env credentials."
            )
        return self.connection

    def schema_details(self, schema_name="public"):
        """Return table names, column details, and sample records as a string."""
        connection = None
        cursor = None

        try:
            connection = self._get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name;
                """,
                (schema_name,),
            )

            tables = cursor.fetchall()
            schema_info = [f"Database Schema: {schema_name}"]

            for table in tables:
                table_name = table["table_name"]
                schema_info.append(f"\nTable: {table_name}")

                cursor.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    ORDER BY ordinal_position;
                    """,
                    (schema_name, table_name),
                )

                columns = cursor.fetchall()

                for column in columns:
                    schema_info.append(
                        f"  Column: {column['column_name']}, "
                        f"Data Type: {column['data_type']}"
                    )

                # Safely quote schema and table identifiers.
                sample_query = sql.SQL(
                    "SELECT * FROM {}.{} LIMIT 5"
                ).format(
                    sql.Identifier(schema_name),
                    sql.Identifier(table_name),
                )

                cursor.execute(sample_query)
                sample_rows = cursor.fetchall()

                schema_info.append("  Sample Data:")
                for row in sample_rows:
                    schema_info.append(f"    {dict(row)}")

            connection.rollback()
            return "\n".join(schema_info)

        except Exception as e:
            if connection and not connection.closed:
                connection.rollback()

            return f"Error fetching schema details: {e}"

        finally:
            if cursor is not None:
                cursor.close()

    def execute_sql(self, query):
        """
        Execute a read-only SQL query and return the result as a string.
        Only SELECT and read-only WITH queries are permitted.
        """
        connection = None
        cursor = None

        try:
            connection = self._get_connection()

            # Enforce read-only mode at the PostgreSQL transaction level.
            cursor = connection.cursor()
            cursor.execute("SET TRANSACTION READ ONLY")

            cursor.execute(query)

            if cursor.description is None:
                connection.rollback()
                return "Error: The query did not return a result set."

            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()

            result = {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }

            connection.rollback()
            return str(result)

        except Exception as e:
            if connection and not connection.closed:
                connection.rollback()

            return f"SQL execution error: {e}"

        finally:
            if cursor is not None:
                cursor.close()

    def close(self):
        """Close the database connection when finished."""
        if self.connection is not None and not self.connection.closed:
            self.connection.close()


def get_database_config():
    """Read PostgreSQL settings from the .env file."""
    password = os.getenv("password")

    if not password:
        raise ValueError(
            "Database password is missing. Set password in your .env file."
        )

    return {
        "host": os.getenv("host", "localhost"),
        "port": int(os.getenv("port", "5432")),
        "user": os.getenv("user", "postgres"),
        "password": password,
        "dbname": os.getenv("database", "postgres"),
    }


if __name__ == "__main__":
    db = DatabaseUtil(get_database_config())

    try:
        schema_info = db.schema_details("public")

        with open("test_schema_details.txt", "w", encoding="utf-8") as file:
            file.write(schema_info)

        print("Schema details saved to test_schema_details.txt")

        result = db.execute_sql(
            "SELECT COUNT(*) AS total_users FROM users"
        )
        print("Database test result:")
        print(result)

    finally:
        db.close()
