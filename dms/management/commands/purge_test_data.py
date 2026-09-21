import sys
from django.core.management.base import BaseCommand
from dms.backup_service import clean_system_data, get_clean_preview_counts


class Command(BaseCommand):
    help = 'Purges test/operational data to prepare the DMS system for official go-live operation.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='test_data',
            choices=['test_data', 'operational', 'factory'],
            help='Cleanup mode: "test_data" (default: wipes system test users, test depts, test vehicles/docs; preserves real officers & real users), "operational" (wipes all docs, attendance, requests, logs), or "factory" (total wipeout).'
        )
        parser.add_argument(
            '--auto-submit', '--yes',
            action='store_true',
            dest='force',
            help='Auto-submit and bypass confirmation prompt.'
        )

    def handle(self, *args, **options):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')

        mode = options['mode']
        force = options['force']

        counts = get_clean_preview_counts()
        self.stdout.write(self.style.WARNING("=== DMS DATA CLEANUP FOR GO-LIVE PREPARATION ==="))
        self.stdout.write(f"Mode: {mode.upper()}")
        if mode == 'test_data':
            self.stdout.write(f"Detected System Test Users: {counts['system_test_users']}")
            self.stdout.write(f"Detected System Test Departments: {counts['system_test_depts']}")
            self.stdout.write(f"Detected System Test Vehicles: {counts['system_test_vehicles']}")
            self.stdout.write(f"Detected System Test Documents: {counts['system_test_docs']}")
            self.stdout.write(f"Total Test Items to Purge: {counts['system_test_total']}")
        else:
            self.stdout.write(f"Current Documents: {counts['documents']} (versions: {counts['document_versions']})")
            self.stdout.write(f"Current Attendance: {counts['attendance']}")
            self.stdout.write(f"Current Vehicle Requests: {counts['vehicle_requests']}")
            self.stdout.write(f"Current Promotion/Medal Requests: {counts['promotion_requests'] + counts['medal_requests']}")
            self.stdout.write(f"Current Audit Logs: {counts['audit_logs']}")
            self.stdout.write(f"Current Civil Servants: {counts['civil_servants']}, Contract Officers: {counts['contract_officers']}")
            self.stdout.write(f"Current Non-Admin Users: {counts['test_users']}")
        self.stdout.write("-" * 50)

        if not force:
            self.stdout.write(self.style.NOTICE("A full Pre-Clean Safety Snapshot will automatically be created before purging."))
            confirm = input("Are you sure you want to proceed? Type 'CONFIRM' to execute (or run with --auto-submit): ").strip()
            if confirm not in ['CONFIRM', 'RESET', 'លុបទិន្នន័យ']:
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return

        self.stdout.write(self.style.NOTICE("Creating Pre-Clean Safety Snapshot & purging data..."))
        result = clean_system_data(user=None, mode=mode)

        if result.get('success'):
            self.stdout.write(self.style.SUCCESS(f"Safety snapshot saved: {result.get('safety_snapshot')}"))
            self.stdout.write(self.style.SUCCESS("Data cleanup completed successfully!"))
            for k, v in result['deleted_counts'].items():
                if v > 0:
                    self.stdout.write(f"  - {k}: {v}")
            self.stdout.write(self.style.SUCCESS(f"Total items removed: {result['total_deleted']}"))
        else:
            self.stdout.write(self.style.ERROR(f"Cleanup failed: {result.get('error')}"))

