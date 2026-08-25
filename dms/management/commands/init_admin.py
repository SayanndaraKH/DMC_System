import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.contrib.auth.models import User
from dms.models import Department, UserProfile, CivilServantProfile, CambodiaProvince

class Command(BaseCommand):
    help = 'Ensures default ADMIN superuser, departments, geography, and seed data exist on startup.'

    def handle(self, *args, **options):
        admin_username = os.environ.get('ADMIN_USERNAME', 'ADMIN').strip()
        admin_password = os.environ.get('ADMIN_PASSWORD', 'syd@168').strip()
        admin_email = os.environ.get('ADMIN_EMAIL', 'sayanndara2022@gmail.com').strip()

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

        # 2. Check and auto-load geo if count is 0
        if CambodiaProvince.objects.count() == 0:
            geo_dump = Path(settings.BASE_DIR) / 'initial_geo.json'
            if geo_dump.exists():
                try:
                    call_command('loaddata', str(geo_dump))
                    self.stdout.write(self.style.SUCCESS("Loaded initial_geo.json"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Geo load note: {e}"))

        # 3. Check and auto-load officers if count is 0
        if CivilServantProfile.objects.count() == 0:
            officers_dump = Path(settings.BASE_DIR) / 'initial_officers.json'
            if officers_dump.exists():
                try:
                    call_command('loaddata', str(officers_dump))
                    self.stdout.write(self.style.SUCCESS("Loaded initial_officers.json"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Officers load note: {e}"))

        # 4. Create or update ADMIN account (both uppercase ADMIN and lowercase admin)
        for uname in [admin_username, 'admin']:
            user = User.objects.filter(username__iexact=uname).first()
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
                user.set_password(admin_password)
                user.is_superuser = True
                user.is_staff = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Updated superuser password for {uname}"))

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
            profile.is_approved = True
            profile.role = 'ADMIN'
            profile.department = lead_dept
            profile.raw_password_display = admin_password
            profile.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully initialized ADMIN with password: {admin_password}"))
