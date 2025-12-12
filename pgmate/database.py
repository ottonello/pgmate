"""Database connection and schema extraction for PostgreSQL."""

import hashlib
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import DatabaseConfig


class DatabaseSchemaExtractor:
    """Extract schema information from PostgreSQL database."""

    def __init__(self, config: DatabaseConfig):
        """Initialize schema extractor.

        Args:
            config: Database configuration
        """
        self.config = config
        self._connection = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def connect(self):
        """Connect to PostgreSQL database."""
        self._connection = psycopg.connect(
            self.config.connection_string,
            row_factory=dict_row,
        )

    def disconnect(self):
        """Disconnect from PostgreSQL database."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def get_database_id(self) -> str:
        """Get unique identifier for this database connection.

        Returns:
            Hash of connection parameters for memory storage
        """
        conn_str = f"{self.config.host}:{self.config.port}/{self.config.database}/{self.config.schema}"
        return hashlib.md5(conn_str.encode()).hexdigest()

    def extract_schema(self) -> dict[str, Any]:
        """Extract complete schema information.

        Returns:
            Dictionary containing schema information
        """
        if not self._connection:
            raise RuntimeError("Not connected to database")

        return {
            "database": self.config.database,
            "schema": self.config.schema,
            "tables": self._get_tables(),
            "relationships": self._get_relationships(),
        }

    def _get_tables(self) -> list[dict[str, Any]]:
        """Get all tables with their columns and metadata.

        Returns:
            List of table information dictionaries
        """
        query = """
            SELECT
                t.table_name,
                t.table_type,
                obj_description(
                    (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
                    'pg_class'
                ) as table_description,
                array_agg(
                    json_build_object(
                        'column_name', c.column_name,
                        'data_type', c.data_type,
                        'is_nullable', c.is_nullable,
                        'column_default', c.column_default,
                        'character_maximum_length', c.character_maximum_length,
                        'numeric_precision', c.numeric_precision,
                        'numeric_scale', c.numeric_scale
                    )
                    ORDER BY c.ordinal_position
                ) as columns
            FROM information_schema.tables t
            JOIN information_schema.columns c
                ON t.table_schema = c.table_schema
                AND t.table_name = c.table_name
            WHERE t.table_schema = %s
                AND t.table_type IN ('BASE TABLE', 'VIEW')
            GROUP BY t.table_schema, t.table_name, t.table_type
            ORDER BY t.table_name;
        """

        with self._connection.cursor() as cur:
            cur.execute(query, (self.config.schema,))
            tables = cur.fetchall()

        # Enrich with primary keys and indexes
        for table in tables:
            table["primary_keys"] = self._get_primary_keys(table["table_name"])
            table["indexes"] = self._get_indexes(table["table_name"])
            table["unique_constraints"] = self._get_unique_constraints(table["table_name"])

        return tables

    def _get_primary_keys(self, table_name: str) -> list[str]:
        """Get primary key columns for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of primary key column names
        """
        query = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid
                AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass
                AND i.indisprimary
            ORDER BY a.attnum;
        """

        with self._connection.cursor() as cur:
            cur.execute(query, (f"{self.config.schema}.{table_name}",))
            return [row["attname"] for row in cur.fetchall()]

    def _get_indexes(self, table_name: str) -> list[dict[str, Any]]:
        """Get indexes for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of index information dictionaries
        """
        query = """
            SELECT
                i.indexname,
                i.indexdef,
                ix.indisunique as is_unique
            FROM pg_indexes i
            JOIN pg_class c ON c.relname = i.indexname
            JOIN pg_index ix ON ix.indexrelid = c.oid
            WHERE i.schemaname = %s
                AND i.tablename = %s
                AND NOT ix.indisprimary
            ORDER BY i.indexname;
        """

        with self._connection.cursor() as cur:
            cur.execute(query, (self.config.schema, table_name))
            return cur.fetchall()

    def _get_unique_constraints(self, table_name: str) -> list[dict[str, Any]]:
        """Get unique constraints for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of unique constraint information
        """
        query = """
            SELECT
                tc.constraint_name,
                array_agg(kcu.column_name ORDER BY kcu.ordinal_position) as columns
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'UNIQUE'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            GROUP BY tc.constraint_name;
        """

        with self._connection.cursor() as cur:
            cur.execute(query, (self.config.schema, table_name))
            return cur.fetchall()

    def _get_relationships(self) -> list[dict[str, Any]]:
        """Get foreign key relationships.

        Returns:
            List of relationship information dictionaries
        """
        query = """
            SELECT
                tc.table_name as from_table,
                kcu.column_name as from_column,
                ccu.table_name as to_table,
                ccu.column_name as to_column,
                tc.constraint_name,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints rc
                ON rc.constraint_name = tc.constraint_name
                AND rc.constraint_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
            ORDER BY tc.table_name, kcu.column_name;
        """

        with self._connection.cursor() as cur:
            cur.execute(query, (self.config.schema,))
            return cur.fetchall()

    def format_schema_for_llm(self) -> str:
        """Format schema information as text for LLM context.

        Returns:
            Formatted schema description
        """
        schema = self.extract_schema()
        lines = [
            f"Database: {schema['database']}",
            f"Schema: {schema['schema']}",
            "",
            "Tables:",
        ]

        for table in schema["tables"]:
            lines.append(f"\n{table['table_name']} ({table['table_type']})")
            if table.get("table_description"):
                lines.append(f"  Description: {table['table_description']}")

            lines.append("  Columns:")
            for col in table["columns"]:
                nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                col_line = f"    - {col['column_name']}: {col['data_type']} {nullable}"
                if col["column_default"]:
                    col_line += f" DEFAULT {col['column_default']}"
                lines.append(col_line)

            if table["primary_keys"]:
                lines.append(f"  Primary Key: {', '.join(table['primary_keys'])}")

            if table["unique_constraints"]:
                lines.append("  Unique Constraints:")
                for uc in table["unique_constraints"]:
                    lines.append(f"    - {uc['constraint_name']}: {', '.join(uc['columns'])}")

            if table["indexes"]:
                lines.append("  Indexes:")
                for idx in table["indexes"]:
                    unique = " (UNIQUE)" if idx["is_unique"] else ""
                    lines.append(f"    - {idx['indexname']}{unique}")

        if schema["relationships"]:
            lines.append("\nRelationships (Foreign Keys):")
            for rel in schema["relationships"]:
                lines.append(
                    f"  - {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']} "
                    f"(ON UPDATE {rel['update_rule']}, ON DELETE {rel['delete_rule']})"
                )

        return "\n".join(lines)
