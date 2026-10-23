from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Synchronizes and resets all PostgreSQL primary key sequences to MAX(id) to prevent duplicate key IntegrityErrors."

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            self.stdout.write(self.style.WARNING(f"Database vendor is '{connection.vendor}'. Sequence reset is only required for PostgreSQL."))
            return

        with connection.cursor() as cur:
            cur.execute("""
                SELECT
                    c.relname AS seq_name,
                    t.relname AS table_name,
                    a.attname AS col_name
                FROM pg_class c
                JOIN pg_depend d ON d.objid = c.oid
                JOIN pg_class t ON t.oid = d.refobjid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
                WHERE c.relkind = 'S'
                ORDER BY t.relname;
            """)
            sequences = cur.fetchall()
            self.stdout.write(f"Found {len(sequences)} PostgreSQL sequences. Synchronizing...")

            fixed_count = 0
            for seq_name, table_name, col_name in sequences:
                try:
                    cur.execute(f'''
                        SELECT setval(
                            '"{seq_name}"',
                            COALESCE((SELECT MAX("{col_name}") FROM "{table_name}"), 1),
                            ((SELECT MAX("{col_name}") FROM "{table_name}") IS NOT NULL)
                        );
                    ''')
                    new_val = cur.fetchone()[0]
                    fixed_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error resetting {table_name}.{col_name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully synchronized all {fixed_count} PostgreSQL sequences!"))
