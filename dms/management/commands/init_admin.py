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

        # 3. Auto-bootstrap initial geography data if database is empty
        try:
            from dms.models import CambodiaProvince, CivilServantProfile
            from django.core.management import call_command
            from pathlib import Path
            from django.conf import settings

            base_path = Path(settings.BASE_DIR)
            geo_file = base_path / 'initial_geo.json'
            officers_file = base_path / 'initial_officers.json'

            if CambodiaProvince.objects.count() == 0 and geo_file.exists():
                self.stdout.write("Loading initial Cambodia geography data (ultra-fast bulk mode)...")
                import json
                from dms.models import CambodiaDistrict, CambodiaCommune, CambodiaVillage
                with open(geo_file, 'r', encoding='utf-8') as f:
                    geo_items = json.load(f)
                provs, dists, comms, vils = [], [], [], []
                for item in geo_items:
                    m = item.get('model')
                    pk = item.get('pk')
                    flds = item.get('fields', {})
                    if m == 'dms.cambodiaprovince':
                        provs.append(CambodiaProvince(code=pk, name_kh=flds.get('name_kh',''), name_en=flds.get('name_en','')))
                    elif m == 'dms.cambodiadistrict':
                        dists.append(CambodiaDistrict(code=pk, name_kh=flds.get('name_kh',''), name_en=flds.get('name_en',''), province_id=flds.get('province')))
                    elif m == 'dms.cambodiacommune':
                        comms.append(CambodiaCommune(code=pk, name_kh=flds.get('name_kh',''), name_en=flds.get('name_en',''), province_id=flds.get('province'), district_id=flds.get('district')))
                    elif m == 'dms.cambodiavillage':
                        vils.append(CambodiaVillage(code=pk, name_kh=flds.get('name_kh',''), name_en=flds.get('name_en',''), province_id=flds.get('province'), district_id=flds.get('district'), commune_id=flds.get('commune')))
                CambodiaProvince.objects.bulk_create(provs)
                CambodiaDistrict.objects.bulk_create(dists, batch_size=2000)
                CambodiaCommune.objects.bulk_create(comms, batch_size=2000)
                CambodiaVillage.objects.bulk_create(vils, batch_size=2000)
                self.stdout.write(self.style.SUCCESS(f"Loaded {len(provs)} provinces, {len(dists)} districts, {len(comms)} communes, {len(vils)} villages."))

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

