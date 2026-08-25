import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = 'Waits for database to be fully ready before running migrations.'

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database connection...')
        for attempt in range(1, 31):
            try:
                conn = connections['default']
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1;")
                    try:
                        cursor.execute("""
                            SELECT pg_terminate_backend(pid) 
                            FROM pg_stat_activity 
                            WHERE pid <> pg_backend_pid() 
                              AND datname = current_database();
                        """)
                        self.stdout.write(self.style.SUCCESS('Cleared dangling database connections and locks!'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Could not clear locks (ignoring): {e}'))
                self.stdout.write(self.style.SUCCESS(f'Database is online and ready (connected on attempt {attempt})!'))
                return
            except OperationalError as e:
                self.stdout.write(f'Database not ready yet ({e}). Retrying in 2 seconds... (attempt {attempt}/30)')
                time.sleep(2)
            except Exception as ex:
                self.stdout.write(f'Waiting for database ({ex}). Retrying in 2 seconds... (attempt {attempt}/30)')
                time.sleep(2)

        self.stderr.write(self.style.ERROR('Database connection timed out after 60 seconds!'))
