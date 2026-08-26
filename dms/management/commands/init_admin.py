import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dms.models import Department, UserProfile

class Command(BaseCommand):
    help = 'Ensures default ADMIN superuser and core departments exist on startup.'

    def handle(self, *args, **options):
        admin_username = os.environ.get('ADMIN_USERNAME', 'ADMIN').strip()
        admin_password = os.environ.get('ADMIN_PASSWORD', 'syd@168').strip()
        admin_email = os.environ.get('ADMIN_EMAIL', 'sayanndara2022@gmail.com').strip()
        # Escape hatch: set ADMIN_PASSWORD_RESET=1 in Railway to force the password
        # back to ADMIN_PASSWORD on the next deploy (then remove the variable).
        force_reset = os.environ.get('ADMIN_PASSWORD_RESET', '').strip().lower() in ('1', 'true', 'yes')

        # 1. Ensure core departments exist
        admin_dept, _ = Department.objects.get_or_create(
            code='ADMIN',
            defaults={
                'name_kh': 'ការិយាល័យកិច្ចការទូទៅ',
                'name_en': 'General Affairs Office',
                'structure_type': 'OLD',
                'order_index': 1,
                'is_active': True,
            }
        )

        lead_dept, _ = Department.objects.get_or_create(
            code='LEAD',
            defaults={
                'name_kh': 'ថ្នាក់ដឹកនាំមន្ទីរ',
                'name_en': 'Provincial Department Leadership',
                'structure_type': 'CORE',
                'order_index': 0,
                'is_active': True,
            }
        )

        # 2. Create or update ADMIN account (both uppercase ADMIN and lowercase admin)
        for uname in [admin_username, 'admin']:
            user = User.objects.filter(username__iexact=uname).first()
            created = user is None
            if not user:
                user = User.objects.create_superuser(
                    username=uname,
                    email=admin_email,
                    password=admin_password,
                    first_name='Admin',
                    last_name='System'
                )
                self.stdout.write(self.style.SUCCESS(f"Created superuser {uname}"))
            else:
                # Never overwrite a password the user changed in the web UI - that
                # silently undid their change on every deploy. Only keep the admin
                # flags, which are what guarantees they can still get in.
                if force_reset:
                    user.set_password(admin_password)
                user.is_superuser = True
                user.is_staff = True
                user.save()
                if force_reset:
                    self.stdout.write(self.style.WARNING(
                        f"ADMIN_PASSWORD_RESET is set - password for {uname} was reset to ADMIN_PASSWORD"
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"Verified superuser {uname} (existing password kept)"
                    ))

            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'department': lead_dept,
                    'role': 'ADMIN',
                    'position_title': 'ប្រធានមន្ទីរ / Administrator',
                    'is_approved': True,
                    'phone': '012 345 678',
                    'can_create_document': True,
                    'can_edit_document': True,
                    'can_route_document': True,
                    'can_annotate': True,
                    'can_complete_document': True,
                    'can_delete_document': True,
                    'can_view_reports': True,
                    'can_print': True,
                }
            )
            # Keep only the two flags that guarantee the admin can still log in and
            # administer. Department and raw_password_display are editable in the web
            # UI, so re-stamping them here would wipe those edits on every deploy.
            profile.is_approved = True
            profile.role = 'ADMIN'
            if created or force_reset:
                profile.raw_password_display = admin_password
            profile.save()

        self.stdout.write(self.style.SUCCESS("ADMIN account and core departments verified."))

        # 3. Auto-bootstrap initial geography data if database is empty
        try:
            from dms.models import CivilServantProfile
            from django.core.management import call_command
            from pathlib import Path
            from django.conf import settings

            base_path = Path(settings.BASE_DIR)
            geo_file = base_path / 'initial_geo.json'
            officers_file = base_path / 'initial_officers.json'

            # load_geo is idempotent and repairs partial loads, so run it every boot.
            if geo_file.exists():
                call_command('load_geo', file=str(geo_file))
            else:
                self.stdout.write(self.style.WARNING(f"initial_geo.json not found at {geo_file}"))

            if CivilServantProfile.objects.count() == 0 and officers_file.exists():
                self.stdout.write("Loading initial civil servants data (56 officers)...")
                call_command('loaddata', str(officers_file))
                self.stdout.write(self.style.SUCCESS(f"Loaded {CivilServantProfile.objects.count()} officers."))

            # Auto-sync status fields if missing on existing profiles
            updated_count = 0
            for p in CivilServantProfile.objects.all():
                needs_save = False
                if not p.framework_category:
                    p.framework_category = p.computed_framework_category
                    needs_save = True
                if not p.highest_degree:
                    p.highest_degree = p.computed_highest_degree
                    needs_save = True
                if not p.officer_status:
                    p.officer_status = p.computed_officer_status
                    needs_save = True
                if needs_save:
                    p.save()
                    updated_count += 1
            if updated_count > 0:
                self.stdout.write(self.style.SUCCESS(f"Auto-synced status and cadre fields for {updated_count} profiles."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Bootstrap note: {e}"))
