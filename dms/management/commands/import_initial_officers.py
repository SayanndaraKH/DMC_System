import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import models

from dms.models import CivilServantProfile, Department


class Command(BaseCommand):
    help = (
        "Loads initial_officers.json, matching Department references by code "
        "instead of trusting the fixture's raw pks (which collide with the "
        "departments migration 0022 already seeds on every fresh deploy)."
    )

    def handle(self, *args, **options):
        fixture_path = Path(settings.BASE_DIR) / 'initial_officers.json'
        if not fixture_path.exists():
            self.stdout.write(self.style.WARNING("initial_officers.json not found, skipping."))
            return

        with open(fixture_path, 'r', encoding='utf-8') as f:
            items = json.load(f)

        # 1. Ensure departments exist, matched by code (not fixture pk); map fixture pk -> real id
        dept_pk_map = {}
        for item in items:
            if item.get('model') != 'dms.department':
                continue
            flds = item.get('fields', {})
            code = flds.get('code')
            if not code:
                continue
            dept, _ = Department.objects.get_or_create(
                code=code,
                defaults={
                    'name_kh': flds.get('name_kh', ''),
                    'name_en': flds.get('name_en', ''),
                    'structure_type': flds.get('structure_type', 'OLD'),
                    'order_index': flds.get('order_index', 0),
                    'is_active': flds.get('is_active', True),
                }
            )
            dept_pk_map[item['pk']] = dept.id

        # 2. Import officer profiles, skipping ones that already exist, remapping FKs by real id
        created, skipped, failed = 0, 0, 0
        for item in items:
            if item.get('model') != 'dms.civilservantprofile':
                continue
            flds = dict(item.get('fields', {}))

            khmer_last = flds.get('khmer_last_name', '')
            khmer_first = flds.get('khmer_first_name', '')
            national_id = flds.get('national_id_number', '')
            officer_id = flds.get('officer_id_number', '')

            dup_filter = models.Q(khmer_last_name=khmer_last, khmer_first_name=khmer_first)
            if national_id:
                dup_filter &= models.Q(national_id_number=national_id)
            elif officer_id:
                dup_filter &= models.Q(officer_id_number=officer_id)
            if CivilServantProfile.objects.filter(dup_filter).exists():
                skipped += 1
                continue

            dept_fixture_pk = flds.pop('department', None)
            flds['department_id'] = dept_pk_map.get(dept_fixture_pk)

            user_pk = flds.pop('user', None)
            flds['user_id'] = user_pk if user_pk and User.objects.filter(pk=user_pk).exists() else None

            created_by_pk = flds.pop('created_by', None)
            flds['created_by_id'] = created_by_pk if created_by_pk and User.objects.filter(pk=created_by_pk).exists() else None

            try:
                CivilServantProfile.objects.create(**flds)
                created += 1
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f"Skipped officer '{khmer_last} {khmer_first}': {e}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"Officers import: {created} created, {skipped} already existed, {failed} failed. "
            f"{len(dept_pk_map)} departments matched/created. "
            f"Note: this restores DATABASE records only -- photo files themselves are not "
            f"in the fixture and must be re-uploaded if the media storage was wiped."
        ))
