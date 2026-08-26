import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from dms.models import (
    CambodiaProvince,
    CambodiaDistrict,
    CambodiaCommune,
    CambodiaVillage,
)

MODEL_MAP = [
    ('dms.cambodiaprovince', CambodiaProvince, ()),
    ('dms.cambodiadistrict', CambodiaDistrict, ('province',)),
    ('dms.cambodiacommune', CambodiaCommune, ('province', 'district')),
    ('dms.cambodiavillage', CambodiaVillage, ('province', 'district', 'commune')),
]


class Command(BaseCommand):
    help = (
        'Loads Cambodia geography (provinces/districts/communes/villages) from '
        'initial_geo.json. Idempotent: only inserts what is missing, so it can '
        'safely re-run on every deploy to repair a partial load.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='Path to initial_geo.json (default: <BASE_DIR>/initial_geo.json)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete all existing geography rows first, then reload from scratch.',
        )

    def handle(self, *args, **options):
        base_path = Path(settings.BASE_DIR)
        geo_file = Path(options['file']) if options['file'] else base_path / 'initial_geo.json'

        if not geo_file.exists():
            self.stderr.write(self.style.ERROR(f'[load_geo] File not found: {geo_file}'))
            return

        if options['force']:
            self.stdout.write('[load_geo] --force: deleting existing geography rows...')
            CambodiaVillage.objects.all().delete()
            CambodiaCommune.objects.all().delete()
            CambodiaDistrict.objects.all().delete()
            CambodiaProvince.objects.all().delete()

        counts_before = {model: model.objects.count() for _, model, _ in MODEL_MAP}
        if all(c > 0 for c in counts_before.values()) and not options['force']:
            self.stdout.write(self.style.SUCCESS(
                '[load_geo] Geography already complete '
                f'({counts_before[CambodiaVillage]} villages) - nothing to do.'
            ))
            return

        self.stdout.write(f'[load_geo] Reading {geo_file}...')
        with open(geo_file, 'r', encoding='utf-8') as f:
            items = json.load(f)

        # Bucket the fixture rows by model so parents are always written first.
        buckets = {name: {} for name, _, _ in MODEL_MAP}
        for item in items:
            bucket = buckets.get(item.get('model'))
            if bucket is None:
                continue
            bucket[item.get('pk')] = item.get('fields', {})

        for name, model, fk_fields in MODEL_MAP:
            rows = buckets[name]
            if not rows:
                continue

            existing = set(model.objects.values_list('pk', flat=True))
            pending = []
            for pk, flds in rows.items():
                if pk in existing:
                    continue
                kwargs = {
                    'code': pk,
                    'name_kh': flds.get('name_kh', ''),
                    'name_en': flds.get('name_en', '') or '',
                }
                for fk in fk_fields:
                    kwargs[f'{fk}_id'] = flds.get(fk)
                pending.append(model(**kwargs))

            if not pending:
                self.stdout.write(f'  -> {model.__name__}: already has all {len(rows)} rows')
                continue

            # ignore_conflicts keeps a re-run safe even if another process raced us.
            model.objects.bulk_create(pending, batch_size=2000, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(
                f'  -> {model.__name__}: inserted {len(pending)} '
                f'(total now {model.objects.count()})'
            ))

        self.stdout.write(self.style.SUCCESS(
            '[load_geo] Done: '
            f'{CambodiaProvince.objects.count()} provinces, '
            f'{CambodiaDistrict.objects.count()} districts, '
            f'{CambodiaCommune.objects.count()} communes, '
            f'{CambodiaVillage.objects.count()} villages.'
        ))
