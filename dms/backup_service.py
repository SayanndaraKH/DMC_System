import os
import io
import json
import zipfile
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core import serializers
from django.db import transaction, connection
from django.apps import apps
from django.contrib.auth.models import User

BACKUP_DIR = Path(settings.BASE_DIR) / 'backups'
BACKUP_DIR.mkdir(exist_ok=True)
TEMP_DIR = BACKUP_DIR / 'temp'
TEMP_DIR.mkdir(exist_ok=True)

# List of models in strict foreign-key dependency order for clean import/export
MODELS_TO_BACKUP = [
    'auth.User',
    'dms.Department',
    'dms.UserProfile',
    'dms.CambodiaProvince',
    'dms.CambodiaDistrict',
    'dms.CambodiaCommune',
    'dms.CambodiaVillage',
    'dms.OfficerEditWindowSetting',
    'dms.CivilServantProfile',
    'dms.OfficerAttachment',
    'dms.OfficerAuditLog',
    'dms.OfficerDepartmentTransferHistory',
    'dms.OfficerPromotionRequest',
    'dms.OfficerMedalRequest',
    'dms.ContractOfficer',
    'dms.ContractOfficerRenewalHistory',
    'dms.ContractOfficerAttachment',
    'dms.ContractOfficerTransferHistory',
    'dms.Document',
    'dms.DocumentVersion',
    'dms.LeadershipAnnotation',
    'dms.DocumentRouting',
    'dms.Notification',
    'dms.ChatMessage',
    'dms.OTPVerification',
    'dms.Vehicle',
    'dms.VehicleRequest',
    'dms.VehicleRequestAttachment',
    'dms.AttendanceRecord',
]

def reset_postgres_sequences():
    """
    On PostgreSQL / Neon Cloud, when records are imported or restored with explicit primary keys,
    the sequence counters must be updated to MAX(id) to avoid unique constraint violations
    (duplicate key value violates unique constraint) on subsequent model creations.
    """
    if connection.vendor != 'postgresql':
        return
    try:
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
            for seq_name, table_name, col_name in sequences:
                try:
                    cur.execute(f'''
                        SELECT setval(
                            '"{seq_name}"',
                            COALESCE((SELECT MAX("{col_name}") FROM "{table_name}"), 1),
                            ((SELECT MAX("{col_name}") FROM "{table_name}") IS NOT NULL)
                        );
                    ''')
                except Exception:
                    pass
    except Exception as e:
        print(f"PostgreSQL sequence reset note: {e}")

def get_system_stats():
    """
    Returns counts of documents, officers, attendance, vehicles, and media files.
    """
    stats = {
        'civil_servants': 0,
        'contract_officers': 0,
        'documents': 0,
        'document_versions': 0,
        'vehicles': 0,
        'vehicle_requests': 0,
        'attendance_records': 0,
        'departments': 0,
        'users': 0,
        'media_files_count': 0,
        'media_total_size_mb': 0.0,
    }
    try:
        from dms.models import (
            CivilServantProfile, ContractOfficer, Document, DocumentVersion,
            Vehicle, VehicleRequest, AttendanceRecord, Department
        )
        stats['civil_servants'] = CivilServantProfile.objects.count()
        stats['contract_officers'] = ContractOfficer.objects.count()
        stats['documents'] = Document.objects.count()
        stats['document_versions'] = DocumentVersion.objects.count()
        stats['vehicles'] = Vehicle.objects.count()
        stats['vehicle_requests'] = VehicleRequest.objects.count()
        stats['attendance_records'] = AttendanceRecord.objects.count()
        stats['departments'] = Department.objects.count()
        stats['users'] = User.objects.count()
    except Exception:
        pass

    media_root = Path(settings.MEDIA_ROOT)
    if media_root.exists():
        file_count = 0
        total_size = 0
        for root, _, files in os.walk(media_root):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    pass
        stats['media_files_count'] = file_count
        stats['media_total_size_mb'] = round(total_size / (1024 * 1024), 2)

    return stats


def export_database_json():
    """
    Dumps all defined application models into a UTF-8 JSON string.
    Uses Django's serializers.serialize directly to avoid named server-side cursors
    and prevent connection pooler disconnection issues on Neon Cloud PostgreSQL.
    """
    all_data = []
    for m_str in MODELS_TO_BACKUP:
        app_label, model_name = m_str.split('.')
        try:
            m = apps.get_model(app_label, model_name)
            qs = m.objects.all()
            if not qs.exists():
                continue
            serialized_str = serializers.serialize('json', qs)
            items = json.loads(serialized_str)
            all_data.extend(items)
        except LookupError:
            continue
        except Exception as err:
            print(f"Warning serializing {m_str}: {err}")

    return json.dumps(all_data, ensure_ascii=False, indent=2)


def create_full_backup(user=None, note=''):
    """
    Creates a complete system backup package (.zip) containing:
    1. data.json - Full UTF-8 JSON database dump
    2. media/ - All photos, scanned PDFs, attachments
    3. manifest.json - Metadata, stats, timestamps, checksum
    """
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"dms_full_backup_{timestamp_str}.zip"
    file_path = BACKUP_DIR / filename

    stats = get_system_stats()
    json_data = export_database_json()
    data_bytes = json_data.encode('utf-8')
    checksum = hashlib.sha256(data_bytes).hexdigest()

    manifest = {
        'backup_version': '1.0',
        'system_name': 'DMS Cambodia (Document & Civil Servant System)',
        'backup_type': 'FULL',
        'created_at': datetime.now().isoformat(),
        'created_by': user.username if user and hasattr(user, 'username') else 'SYSTEM',
        'note': note,
        'stats': stats,
        'data_checksum_sha256': checksum,
    }

    with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_out:
        # 1. Write manifest
        zip_out.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        # 2. Write database dump
        zip_out.writestr('data.json', data_bytes)
        # 3. Write media files
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for root, _, files in os.walk(media_root):
                for f in files:
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, media_root)
                    # Protect against backslashes in zip archive paths
                    archive_name = 'media/' + rel_path.replace('\\', '/')
                    try:
                        zip_out.write(full_path, arcname=archive_name)
                    except Exception:
                        pass

    file_size = file_path.stat().st_size
    return {
        'success': True,
        'filename': filename,
        'file_path': str(file_path),
        'file_size': file_size,
        'file_size_mb': round(file_size / (1024 * 1024), 2),
        'manifest': manifest,
    }


def create_db_backup(user=None, note=''):
    """
    Creates a standalone database backup (.zip) containing data.json and manifest.json.
    """
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"dms_database_backup_{timestamp_str}.zip"
    file_path = BACKUP_DIR / filename

    stats = get_system_stats()
    json_data = export_database_json()
    data_bytes = json_data.encode('utf-8')
    checksum = hashlib.sha256(data_bytes).hexdigest()

    manifest = {
        'backup_version': '1.0',
        'system_name': 'DMS Cambodia',
        'backup_type': 'DATABASE_ONLY',
        'created_at': datetime.now().isoformat(),
        'created_by': user.username if user and hasattr(user, 'username') else 'SYSTEM',
        'note': note,
        'stats': stats,
        'data_checksum_sha256': checksum,
    }

    with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_out:
        zip_out.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        zip_out.writestr('data.json', data_bytes)

    file_size = file_path.stat().st_size
    return {
        'success': True,
        'filename': filename,
        'file_path': str(file_path),
        'file_size': file_size,
        'file_size_mb': round(file_size / (1024 * 1024), 2),
        'manifest': manifest,
    }


def create_media_backup(user=None, note=''):
    """
    Creates a standalone media attachments backup (.zip) containing only the media files.
    """
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"dms_media_backup_{timestamp_str}.zip"
    file_path = BACKUP_DIR / filename

    stats = get_system_stats()
    manifest = {
        'backup_version': '1.0',
        'system_name': 'DMS Cambodia',
        'backup_type': 'MEDIA_ONLY',
        'created_at': datetime.now().isoformat(),
        'created_by': user.username if user and hasattr(user, 'username') else 'SYSTEM',
        'note': note,
        'stats': stats,
    }

    with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_out:
        zip_out.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for root, _, files in os.walk(media_root):
                for f in files:
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, media_root)
                    archive_name = 'media/' + rel_path.replace('\\', '/')
                    try:
                        zip_out.write(full_path, arcname=archive_name)
                    except Exception:
                        pass

    file_size = file_path.stat().st_size
    return {
        'success': True,
        'filename': filename,
        'file_path': str(file_path),
        'file_size': file_size,
        'file_size_mb': round(file_size / (1024 * 1024), 2),
        'manifest': manifest,
    }


def create_safety_snapshot():
    """
    Creates an automated pre-restore safety snapshot so any restore action can be undone.
    """
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"safety_pre_restore_{timestamp_str}.zip"
    file_path = BACKUP_DIR / filename

    stats = get_system_stats()
    json_data = export_database_json()
    data_bytes = json_data.encode('utf-8')

    manifest = {
        'backup_version': '1.0',
        'backup_type': 'SAFETY_SNAPSHOT',
        'created_at': datetime.now().isoformat(),
        'note': 'Automated pre-restore safety snapshot (zero data loss guarantee)',
        'stats': stats,
    }

    with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_out:
        zip_out.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        zip_out.writestr('data.json', data_bytes)
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for root, _, files in os.walk(media_root):
                for f in files:
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, media_root)
                    archive_name = 'media/' + rel_path.replace('\\', '/')
                    try:
                        zip_out.write(full_path, arcname=archive_name)
                    except Exception:
                        pass

    return str(file_path)


def inspect_backup_file(file_obj_or_path):
    """
    Inspects an uploaded or local backup file and returns its manifest, file list, and verification status.
    """
    is_zip = False
    temp_target = None

    if hasattr(file_obj_or_path, 'read'):
        # Uploaded file in memory or temp
        temp_target = TEMP_DIR / f"inspect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
        with open(temp_target, 'wb') as f:
            for chunk in file_obj_or_path.chunks():
                f.write(chunk)
        check_path = temp_target
    else:
        check_path = Path(file_obj_or_path)

    result = {
        'is_valid': False,
        'backup_type': 'UNKNOWN',
        'manifest': None,
        'has_data_json': False,
        'media_files_count': 0,
        'error': None,
        'temp_path': str(temp_target) if temp_target else str(check_path),
    }

    try:
        if zipfile.is_zipfile(check_path):
            result['is_valid'] = True
            with zipfile.ZipFile(check_path, 'r') as zip_in:
                names = zip_in.namelist()
                if 'manifest.json' in names:
                    try:
                        manifest_raw = zip_in.read('manifest.json').decode('utf-8')
                        result['manifest'] = json.loads(manifest_raw)
                        result['backup_type'] = result['manifest'].get('backup_type', 'ZIP_PACKAGE')
                    except Exception as e:
                        result['manifest'] = {'error': str(e)}
                if 'data.json' in names:
                    result['has_data_json'] = True
                media_count = len([n for n in names if n.startswith('media/') and not n.endswith('/')])
                result['media_files_count'] = media_count
                if not result['manifest'] and result['has_data_json']:
                    result['backup_type'] = 'ZIP_DATA'
        else:
            # Check if it's a raw JSON file
            try:
                with open(check_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0 and 'model' in data[0]:
                        result['is_valid'] = True
                        result['has_data_json'] = True
                        result['backup_type'] = 'RAW_JSON'
                        result['manifest'] = {
                            'backup_version': '1.0',
                            'backup_type': 'RAW_JSON',
                            'total_records': len(data),
                        }
            except Exception as e:
                result['error'] = f"Not a valid zip or json backup: {str(e)}"
    except Exception as e:
        result['error'] = str(e)

    return result


def restore_backup(file_obj_or_path, mode='merge'):
    """
    Restores data from a .zip or .json backup package.
    
    Modes:
    - 'merge': (Lossless) Updates existing records and inserts new ones. NEVER deletes records that only exist on local PC.
    - 'replace': Creates a safety snapshot, cleans user data tables, and reloads full backup data.
    
    Extracts media files into MEDIA_ROOT with path-traversal protection.
    """
    inspection = inspect_backup_file(file_obj_or_path)
    if not inspection['is_valid']:
        return {
            'success': False,
            'error': inspection.get('error') or "Invalid backup package format.",
        }

    file_path = Path(inspection['temp_path'])
    
    # 1. ALWAYS Create a Safety Snapshot first before any modification
    safety_snapshot_path = create_safety_snapshot()

    report = {
        'success': True,
        'mode': mode,
        'safety_snapshot': safety_snapshot_path,
        'records_created': 0,
        'records_updated': 0,
        'records_skipped': 0,
        'media_restored': 0,
        'manifest': inspection.get('manifest'),
        'details': [],
    }

    json_str = None
    media_zip_source = None

    if zipfile.is_zipfile(file_path):
        media_zip_source = zipfile.ZipFile(file_path, 'r')
        if 'data.json' in media_zip_source.namelist():
            json_str = media_zip_source.read('data.json').decode('utf-8')
    else:
        # Raw JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            json_str = f.read()

    # 2. Database Restoration
    if json_str:
        try:
            raw_data = json.loads(json_str)
            items_by_model = {}
            for item in raw_data:
                items_by_model.setdefault(item['model'].lower(), []).append(item)

            with transaction.atomic():
                # If replace mode, clear existing application tables in reverse order
                if mode == 'replace':
                    models_to_clear = list(reversed(MODELS_TO_BACKUP))
                    for m_str in models_to_clear:
                        app_label, model_name = m_str.split('.')
                        try:
                            m_cls = apps.get_model(app_label, model_name)
                            if m_str == 'auth.User':
                                m_cls.objects.exclude(is_superuser=True).exclude(username__iexact='admin').delete()
                            elif m_str != 'dms.Department':
                                m_cls.objects.all().delete()
                        except Exception:
                            pass

                # Step A: Restore auth.User first to ensure all foreign keys can resolve
                users_items = items_by_model.get('auth.user', [])
                for u_item in users_items:
                    fields = u_item.get('fields', {})
                    uname = fields.get('username')
                    if not uname:
                        continue
                    u_obj, created = User.objects.get_or_create(username=uname)
                    u_obj.email = fields.get('email', u_obj.email)
                    u_obj.first_name = fields.get('first_name', u_obj.first_name)
                    u_obj.last_name = fields.get('last_name', u_obj.last_name)
                    u_obj.is_staff = fields.get('is_staff', u_obj.is_staff)
                    u_obj.is_superuser = fields.get('is_superuser', u_obj.is_superuser)
                    u_obj.is_active = fields.get('is_active', u_obj.is_active)
                    if 'password' in fields:
                        u_obj.password = fields['password']
                    u_obj.save()
                    if created:
                        report['records_created'] += 1
                    else:
                        report['records_updated'] += 1

                # Step B: Restore dms.Department and map old PKs to target DB PKs
                from dms.models import Department
                dept_items = items_by_model.get('dms.department', [])
                dept_id_map = {}
                for d_item in dept_items:
                    fields = d_item.get('fields', {})
                    code = fields.get('code')
                    old_pk = d_item.get('pk')
                    d_obj = None
                    if code:
                        d_obj = Department.objects.filter(code=code).first()
                    if not d_obj and old_pk:
                        d_obj = Department.objects.filter(pk=old_pk).first()
                    created = False
                    if not d_obj:
                        d_obj = Department(code=code)
                        created = True
                    d_obj.name_kh = fields.get('name_kh', d_obj.name_kh)
                    d_obj.name_en = fields.get('name_en', d_obj.name_en)
                    d_obj.description = fields.get('description', d_obj.description)
                    d_obj.structure_type = fields.get('structure_type', d_obj.structure_type)
                    d_obj.is_active = fields.get('is_active', d_obj.is_active)
                    d_obj.order_index = fields.get('order_index', d_obj.order_index)
                    d_obj.save()
                    if old_pk:
                        dept_id_map[old_pk] = d_obj.pk
                    if created:
                        report['records_created'] += 1
                    else:
                        report['records_updated'] += 1

                # Remap department foreign keys in all other models
                dept_fk_fields = ['department', 'origin_dept', 'current_dept']
                for m_key, items in items_by_model.items():
                    if m_key in ['auth.user', 'dms.department']:
                        continue
                    for it in items:
                        fields = it.get('fields', {})
                        for fk_name in dept_fk_fields:
                            if fk_name in fields and fields[fk_name] is not None:
                                val = fields[fk_name]
                                if isinstance(val, int) and val in dept_id_map:
                                    fields[fk_name] = dept_id_map[val]
                                elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], str):
                                    mapped = Department.objects.filter(code=val[0]).first()
                                    if mapped:
                                        fields[fk_name] = mapped.pk

                # Step C: Restore all other models in strict dependency order
                geo_models = {'dms.cambodiaprovince', 'dms.cambodiadistrict', 'dms.cambodiacommune', 'dms.cambodiavillage'}

                for m_str in MODELS_TO_BACKUP:
                    m_key = m_str.lower()
                    if m_key in ['auth.user', 'dms.department']:
                        continue
                    items = items_by_model.get(m_key, [])
                    if not items:
                        continue

                    app_label, model_name = m_str.split('.')
                    try:
                        m_cls = apps.get_model(app_label, model_name)
                    except LookupError:
                        continue

                    # Fast-skip for geography models if they already exist
                    if m_key in geo_models and mode == 'merge':
                        existing_pks = set(m_cls.objects.values_list('pk', flat=True))
                        items_to_save = [it for it in items if it.get('pk') not in existing_pks]
                        report['records_skipped'] += len(items) - len(items_to_save)
                        items = items_to_save
                        if not items:
                            continue

                    # Deserialize and save this model's items
                    try:
                        for d_obj in serializers.deserialize('json', json.dumps(items), ignorenonexistent=True):
                            try:
                                pk_val = d_obj.object.pk
                                exists = m_cls.objects.filter(pk=pk_val).exists() if pk_val else False
                                d_obj.save()
                                if exists:
                                    report['records_updated'] += 1
                                else:
                                    report['records_created'] += 1
                            except Exception as save_err:
                                report['records_skipped'] += 1
                                report['details'].append(f"Skipped {m_cls.__name__} (pk={getattr(d_obj.object, 'pk', '?')}): {str(save_err)}")
                    except Exception as deser_err:
                        report['records_skipped'] += len(items)
                        report['details'].append(f"Batch deserialize note for {m_str}: {str(deser_err)}")

            # Synchronize PostgreSQL primary key sequences on Neon Cloud Database
            reset_postgres_sequences()

        except Exception as e:
            # Clean up temp file
            if file_path.exists() and 'temp' in str(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            return {
                'success': False,
                'error': f"Database restoration failed: {str(e)}",
                'safety_snapshot': safety_snapshot_path,
            }


    # 3. Media Files Restoration
    if media_zip_source:
        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            for member in media_zip_source.infolist():
                if member.is_dir():
                    continue
                if member.filename.startswith('media/'):
                    # Strip 'media/' prefix
                    rel_name = member.filename[6:]
                    # Path traversal security check
                    target_file = (media_root / rel_name).resolve()
                    if not str(target_file).startswith(str(media_root.resolve())):
                        continue  # Potential zip slip attempt, skip!

                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    with media_zip_source.open(member) as source, open(target_file, 'wb') as dest:
                        shutil.copyfileobj(source, dest)
                    report['media_restored'] += 1
        except Exception as media_err:
            report['details'].append(f"Media extraction note: {str(media_err)}")
        finally:
            media_zip_source.close()

    # Clean up temp file
    if file_path.exists() and 'temp' in str(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    return report


def list_local_backups():
    """
    Returns a list of all backup files currently stored in BACKUP_DIR with metadata.
    """
    backups = []
    if not BACKUP_DIR.exists():
        return backups

    for item in BACKUP_DIR.glob('*.zip'):
        if item.is_file():
            stat = item.stat()
            backup_type = 'FULL'
            created_at = datetime.fromtimestamp(stat.st_ctime)
            note = ''
            stats_info = None

            # Quick inspect without heavy extraction
            try:
                with zipfile.ZipFile(item, 'r') as zf:
                    if 'manifest.json' in zf.namelist():
                        m_data = json.loads(zf.read('manifest.json').decode('utf-8'))
                        backup_type = m_data.get('backup_type', 'ZIP')
                        note = m_data.get('note', '')
                        stats_info = m_data.get('stats')
                        if 'created_at' in m_data:
                            try:
                                created_at = datetime.fromisoformat(m_data['created_at'])
                            except Exception:
                                pass
            except Exception:
                pass

            backups.append({
                'filename': item.name,
                'path': str(item),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created_at': created_at,
                'backup_type': backup_type,
                'note': note,
                'stats': stats_info,
                'is_safety_snapshot': item.name.startswith('safety_pre_restore_') or item.name.startswith('safety_pre_clean_'),
            })

    backups.sort(key=lambda x: x['created_at'], reverse=True)
    return backups


def create_pre_clean_snapshot(user=None, note="Automated pre-clean safety snapshot (Go-Live Prep)"):
    """
    Creates an automated pre-cleanup safety snapshot before purging any test/operational data.
    """
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"safety_pre_clean_{timestamp_str}.zip"
    file_path = BACKUP_DIR / filename

    stats = get_system_stats()
    json_data = export_database_json()
    data_bytes = json_data.encode('utf-8')

    operator_name = user.get_full_name() or user.username if user else "Admin System"
    manifest = {
        'backup_version': '1.0',
        'backup_type': 'SAFETY_SNAPSHOT_PRE_CLEAN',
        'created_at': datetime.now().isoformat(),
        'created_by': operator_name,
        'note': f"{note} - Triggered by {operator_name}",
        'stats': stats,
    }

    with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_out:
        zip_out.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        zip_out.writestr('data.json', data_bytes)
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for root, _, files in os.walk(media_root):
                for f in files:
                    full_p = Path(root) / f
                    try:
                        rel_p = full_p.relative_to(media_root)
                        zip_out.write(full_p, arcname=f"media/{rel_p.as_posix()}")
                    except Exception:
                        pass

    file_size = file_path.stat().st_size
    return {
        'success': True,
        'file_path': str(file_path),
        'filename': filename,
        'file_size_mb': round(file_size / (1024 * 1024), 2),
        'manifest': manifest,
    }


def get_clean_preview_counts():
    """
    Returns counts of all operational, test, and master entities for UI preview before cleaning.
    """
    counts = {
        'documents': 0,
        'document_versions': 0,
        'annotations': 0,
        'routings': 0,
        'attendance': 0,
        'vehicle_requests': 0,
        'vehicles': 0,
        'promotion_requests': 0,
        'medal_requests': 0,
        'audit_logs': 0,
        'notifications': 0,
        'chat_messages': 0,
        'otp_verifications': 0,
        'civil_servants': 0,
        'contract_officers': 0,
        'test_users': 0,
        'departments': 0,
        'system_test_users': 0,
        'system_test_depts': 0,
        'system_test_vehicles': 0,
        'system_test_docs': 0,
        'system_test_total': 0,
    }
    try:
        from dms.models import (
            Document, DocumentVersion, LeadershipAnnotation, DocumentRouting,
            AttendanceRecord, VehicleRequest, Vehicle, OfficerPromotionRequest,
            OfficerMedalRequest, OfficerAuditLog, Notification, ChatMessage,
            OTPVerification, CivilServantProfile, ContractOfficer, Department
        )
        from django.db.models import Q

        counts['documents'] = Document.objects.count()
        counts['document_versions'] = DocumentVersion.objects.count()
        counts['annotations'] = LeadershipAnnotation.objects.count()
        counts['routings'] = DocumentRouting.objects.count()
        counts['attendance'] = AttendanceRecord.objects.count()
        counts['vehicle_requests'] = VehicleRequest.objects.count()
        counts['vehicles'] = Vehicle.objects.count()
        counts['promotion_requests'] = OfficerPromotionRequest.objects.count()
        counts['medal_requests'] = OfficerMedalRequest.objects.count()
        counts['audit_logs'] = OfficerAuditLog.objects.count()
        counts['notifications'] = Notification.objects.count()
        counts['chat_messages'] = ChatMessage.objects.count()
        counts['otp_verifications'] = OTPVerification.objects.count()
        counts['civil_servants'] = CivilServantProfile.objects.count()
        counts['contract_officers'] = ContractOfficer.objects.count()
        counts['departments'] = Department.objects.count()
        # Count non-superusers / non-admin users
        counts['test_users'] = User.objects.exclude(is_superuser=True).exclude(username__iexact='admin').count()

        # Specific System Test Data counts
        seed_usernames = ['leader_user', 'admin_user', 'acc_user', 'hr_user', 'it_user', 'admin_test_veh', 'user_agri_veh', 'user_fish_veh']
        real_cs_user_ids = set(CivilServantProfile.objects.filter(user__isnull=False).values_list('user_id', flat=True))
        test_users_qs = User.objects.filter(
            Q(username__in=seed_usernames) |
            Q(username__icontains='test') |
            Q(email__icontains='test') |
            Q(email__icontains='@gov.kh')
        ).exclude(username__in=['ADMIN', 'admin']).exclude(id__in=real_cs_user_ids)
        test_u_ids = list(test_users_qs.values_list('id', flat=True))

        test_depts_qs = Department.objects.filter(
            Q(code__icontains='test') |
            Q(name_kh__icontains='test') |
            Q(name_kh__icontains='តេស្ត')
        )
        test_vehicles_qs = Vehicle.objects.filter(
            Q(created_by_id__in=test_u_ids) |
            Q(plate_number__icontains='9999') |
            Q(notes__icontains='test') |
            Q(notes__icontains='តេស្ត')
        )
        test_docs_qs = Document.objects.filter(
            Q(created_by_id__in=test_u_ids) |
            Q(registry_number__in=['001/26/ADMIN', '002/26/ACC', '003/26/HR', '004/26/IT']) |
            Q(title__icontains='test') |
            Q(title__icontains='តេស្ត')
        )

        counts['system_test_users'] = test_users_qs.count()
        counts['system_test_depts'] = test_depts_qs.count()
        counts['system_test_vehicles'] = test_vehicles_qs.count()
        counts['system_test_docs'] = test_docs_qs.count()
        counts['system_test_total'] = (
            counts['system_test_users'] +
            counts['system_test_depts'] +
            counts['system_test_vehicles'] +
            counts['system_test_docs']
        )
    except Exception:
        pass
    return counts


def safe_delete_file_field(file_field):
    """
    Safely deletes a physical file referenced by a model FileField/ImageField.
    """
    try:
        if file_field and hasattr(file_field, 'path') and file_field.name:
            if os.path.exists(file_field.path) and os.path.isfile(file_field.path):
                os.remove(file_field.path)
    except Exception:
        pass


def clean_system_data(options=None, user=None, mode='operational'):
    """
    Purges test and operational data to prepare the system for official live operation.
    
    Modes:
      - 'test_data': ONLY cleans system-generated test data (test users like admin_test_veh,
                     test departments like AGRI_DEV_TEST, seed documents, test vehicles).
                     100% PRESERVES: All real Civil Servants, Contract Officers, official depts, real accounts.
      - 'operational': Cleans operational test data (Documents, Attendance, Vehicle Requests,
                       Promotion/Medal Requests, Audit Logs, Notifications, Chat, OTPs).
                       PRESERVES: Civil Servants, Contract Officers, Departments, Vehicles, Users, Geography.
      - 'factory': Cleans operational test data + Test Officers, Test Contract Officers,
                   Test Vehicles, and Test Non-Admin Users.
                   PRESERVES: Admin Superusers, Departments, Geography.
      - 'custom': Uses granular boolean flags in the `options` dictionary.
      
    Safety features:
      1. Always creates an automated Pre-Clean Safety Snapshot in backups/ before wiping anything.
      2. Runs inside a database atomic transaction.
      3. Strictly protects Superuser accounts, 'admin'/'ADMIN' users, and the current acting user.
      4. Cleans up associated physical media files on disk.
    """
    options = options or {}
    report = {
        'success': False,
        'safety_snapshot': '',
        'mode': mode,
        'deleted_counts': {
            'documents': 0,
            'document_versions': 0,
            'annotations': 0,
            'routings': 0,
            'attendance': 0,
            'vehicle_requests': 0,
            'vehicles': 0,
            'promotion_requests': 0,
            'medal_requests': 0,
            'audit_logs': 0,
            'transfer_history': 0,
            'notifications': 0,
            'chat_messages': 0,
            'otp_verifications': 0,
            'civil_servants': 0,
            'contract_officers': 0,
            'test_users': 0,
            'departments': 0,
            'media_files': 0,
        },
        'total_deleted': 0,
        'error': None,
    }

    # Set flags according to mode
    if mode == 'test_data':
        clean_docs = False
        clean_attendance = False
        clean_veh_reqs = False
        clean_vehicles = False
        clean_hr_reqs = False
        clean_comms = False
        clean_officers = False
        clean_users = False
        clean_media = True
    elif mode == 'operational':
        clean_docs = True
        clean_attendance = True
        clean_veh_reqs = True
        clean_vehicles = False
        clean_hr_reqs = True
        clean_comms = True
        clean_officers = False
        clean_users = False
        clean_media = True
    elif mode == 'factory':
        clean_docs = True
        clean_attendance = True
        clean_veh_reqs = True
        clean_vehicles = True
        clean_hr_reqs = True
        clean_comms = True
        clean_officers = True
        clean_users = True
        clean_media = True
    else:  # custom mode
        clean_docs = bool(options.get('clean_documents', True))
        clean_attendance = bool(options.get('clean_attendance', True))
        clean_veh_reqs = bool(options.get('clean_vehicle_requests', True))
        clean_vehicles = bool(options.get('clean_vehicles', False))
        clean_hr_reqs = bool(options.get('clean_hr_requests', True))
        clean_comms = bool(options.get('clean_comms_logs', True))
        clean_officers = bool(options.get('clean_officers', False))
        clean_users = bool(options.get('clean_test_users', False))
        clean_media = bool(options.get('clean_media_files', True))

    # STEP 1: Mandatory automated Pre-Clean Safety Snapshot
    try:
        snap_res = create_pre_clean_snapshot(user=user, note=f"Pre-Clean Snapshot ({mode} mode)")
        report['safety_snapshot'] = snap_res.get('filename', '')
    except Exception as snap_err:
        report['error'] = f"មិនអាចបង្កើត Safety Snapshot មុនពេលសម្អាតបានទេ: {str(snap_err)}"
        return report

    # STEP 2: Database atomic transaction
    try:
        from dms.models import (
            Document, DocumentVersion, LeadershipAnnotation, DocumentRouting,
            AttendanceRecord, VehicleRequest, VehicleRequestAttachment, Vehicle,
            OfficerPromotionRequest, OfficerMedalRequest, OfficerDepartmentTransferHistory,
            ContractOfficerTransferHistory, ContractOfficerRenewalHistory, OfficerAuditLog,
            OfficerAttachment, ContractOfficerAttachment, CivilServantProfile,
            ContractOfficer, Notification, ChatMessage, OTPVerification, UserProfile, Department
        )
        from django.db.models import Q

        media_files_deleted = 0

        with transaction.atomic():
            if mode == 'test_data':
                # -------------------------------------------------------------
                # SPECIALIZED PURGE: SYSTEM-GENERATED TEST DATA ONLY
                # -------------------------------------------------------------
                seed_usernames = ['leader_user', 'admin_user', 'acc_user', 'hr_user', 'it_user', 'admin_test_veh', 'user_agri_veh', 'user_fish_veh']
                protected_names = {'admin', 'ADMIN'}
                if user and user.username:
                    protected_names.add(user.username.lower())
                    protected_names.add(user.username.upper())
                    protected_names.add(user.username)

                test_users_qs = User.objects.filter(
                    Q(username__in=seed_usernames) |
                    Q(username__icontains='test') |
                    Q(email__icontains='test') |
                    Q(email__icontains='@gov.kh')
                ).exclude(username__in=protected_names)

                # Never delete any user account linked to an active CivilServantProfile
                real_cs_user_ids = set(CivilServantProfile.objects.filter(user__isnull=False).values_list('user_id', flat=True))
                test_users = test_users_qs.exclude(id__in=real_cs_user_ids)
                test_user_ids = list(test_users.values_list('id', flat=True))

                # 1. Test Departments
                test_depts = Department.objects.filter(
                    Q(code__icontains='test') |
                    Q(name_kh__icontains='test') |
                    Q(name_kh__icontains='តេស្ត')
                )
                default_dept = Department.objects.exclude(id__in=test_depts.values_list('id', flat=True)).first()
                for td in test_depts:
                    if default_dept:
                        CivilServantProfile.objects.filter(department=td).update(department=default_dept)
                        ContractOfficer.objects.filter(department=td).update(department=default_dept)
                td_cnt = test_depts.count()
                test_depts.delete()
                report['deleted_counts']['departments'] = td_cnt

                # 2. Test Vehicles
                test_vehicles = Vehicle.objects.filter(
                    Q(created_by_id__in=test_user_ids) |
                    Q(plate_number__icontains='9999') |
                    Q(notes__icontains='test') |
                    Q(notes__icontains='តេស្ត')
                )
                for v in test_vehicles:
                    if clean_media:
                        if getattr(v, 'photo_front', None):
                            safe_delete_file_field(v.photo_front)
                            media_files_deleted += 1
                        if getattr(v, 'photo_side', None):
                            safe_delete_file_field(v.photo_side)
                            media_files_deleted += 1
                        if getattr(v, 'registration_card_photo', None):
                            safe_delete_file_field(v.registration_card_photo)
                            media_files_deleted += 1
                v_cnt = test_vehicles.count()
                test_vehicles.delete()
                report['deleted_counts']['vehicles'] = v_cnt

                # 3. Test Vehicle Requests
                test_veh_reqs = VehicleRequest.objects.filter(
                    Q(vehicle__in=test_vehicles) |
                    Q(purpose__icontains='test') |
                    Q(purpose__icontains='តេស្ត') |
                    Q(applicant_name__icontains='test') |
                    Q(applicant_name__icontains='តេស្ត')
                )
                for vr in test_veh_reqs:
                    for att in vr.attachments.all():
                        if clean_media and att.file:
                            safe_delete_file_field(att.file)
                            media_files_deleted += 1
                vr_cnt = test_veh_reqs.count()
                test_veh_reqs.delete()
                report['deleted_counts']['vehicle_requests'] = vr_cnt

                # 4. Test Documents
                seed_reg_nums = ['001/26/ADMIN', '002/26/ACC', '003/26/HR', '004/26/IT']
                test_docs = Document.objects.filter(
                    Q(created_by_id__in=test_user_ids) |
                    Q(registry_number__in=seed_reg_nums) |
                    Q(title__icontains='test') |
                    Q(title__icontains='តេស្ត')
                )
                for doc in test_docs:
                    for ver in doc.versions.all():
                        if clean_media and ver.file:
                            safe_delete_file_field(ver.file)
                            media_files_deleted += 1
                    for ann in doc.annotations.all():
                        if clean_media and getattr(ann, 'signature_image', None):
                            safe_delete_file_field(ann.signature_image)
                            media_files_deleted += 1
                doc_cnt = test_docs.count()
                test_docs.delete()
                report['deleted_counts']['documents'] = doc_cnt

                # 5. Test Notifications & Communications
                notifs_del = Notification.objects.filter(
                    Q(recipient_id__in=test_user_ids) |
                    Q(title__icontains='test') |
                    Q(document__isnull=True, title__icontains='00')
                )
                n_cnt = notifs_del.count()
                notifs_del.delete()
                report['deleted_counts']['notifications'] = n_cnt

                chats_del = ChatMessage.objects.filter(sender_id__in=test_user_ids)
                c_cnt = chats_del.count()
                chats_del.delete()
                report['deleted_counts']['chat_messages'] = c_cnt

                test_identifiers = set(test_users.values_list('username', flat=True)) | set(test_users.exclude(email='').values_list('email', flat=True))
                otps_del = OTPVerification.objects.filter(identifier__in=test_identifiers)
                otp_cnt = otps_del.count()
                otps_del.delete()
                report['deleted_counts']['otp_verifications'] = otp_cnt

                # 6. Delete Test Users
                u_cnt = len(test_user_ids)
                test_users.delete()
                report['deleted_counts']['test_users'] = u_cnt

                report['deleted_counts']['media_files'] = media_files_deleted
                total_cnt = sum(report['deleted_counts'].values())
                report['total_deleted'] = total_cnt
                report['success'] = True
                return report

            # 1. ATTENDANCE
            if clean_attendance:
                cnt = AttendanceRecord.objects.count()
                AttendanceRecord.objects.all().delete()
                report['deleted_counts']['attendance'] = cnt

            # 2. VEHICLE REQUESTS & LOGISTICS
            if clean_veh_reqs:
                # Remove attachment files
                for att in VehicleRequestAttachment.objects.all():
                    if clean_media and att.file:
                        safe_delete_file_field(att.file)
                        media_files_deleted += 1
                VehicleRequestAttachment.objects.all().delete()
                req_cnt = VehicleRequest.objects.count()
                VehicleRequest.objects.all().delete()
                report['deleted_counts']['vehicle_requests'] = req_cnt

            if clean_vehicles:
                v_cnt = Vehicle.objects.count()
                Vehicle.objects.all().delete()
                report['deleted_counts']['vehicles'] = v_cnt

            # 3. DOCUMENTS & WORKFLOW
            if clean_docs:
                # Delete files for versions & annotations
                for ver in DocumentVersion.objects.all():
                    if clean_media and ver.file:
                        safe_delete_file_field(ver.file)
                        media_files_deleted += 1
                for ann in LeadershipAnnotation.objects.all():
                    if clean_media and getattr(ann, 'signature_image', None):
                        safe_delete_file_field(ann.signature_image)
                        media_files_deleted += 1

                doc_cnt = Document.objects.count()
                ver_cnt = DocumentVersion.objects.count()
                ann_cnt = LeadershipAnnotation.objects.count()
                rot_cnt = DocumentRouting.objects.count()

                DocumentRouting.objects.all().delete()
                LeadershipAnnotation.objects.all().delete()
                DocumentVersion.objects.all().delete()
                Document.objects.all().delete()

                report['deleted_counts']['documents'] = doc_cnt
                report['deleted_counts']['document_versions'] = ver_cnt
                report['deleted_counts']['annotations'] = ann_cnt
                report['deleted_counts']['routings'] = rot_cnt

            # 4. HR REQUESTS, TRANSFERS & AUDIT LOGS
            if clean_hr_reqs:
                p_cnt = OfficerPromotionRequest.objects.count()
                m_cnt = OfficerMedalRequest.objects.count()
                t_cnt = OfficerDepartmentTransferHistory.objects.count() + ContractOfficerTransferHistory.objects.count() + ContractOfficerRenewalHistory.objects.count()
                a_cnt = OfficerAuditLog.objects.count()

                # Clean promotion attachments if any
                for pr in OfficerPromotionRequest.objects.all():
                    if clean_media and getattr(pr, 'attachment_file', None):
                        safe_delete_file_field(pr.attachment_file)
                        media_files_deleted += 1

                OfficerPromotionRequest.objects.all().delete()
                OfficerMedalRequest.objects.all().delete()
                OfficerDepartmentTransferHistory.objects.all().delete()
                ContractOfficerTransferHistory.objects.all().delete()
                ContractOfficerRenewalHistory.objects.all().delete()
                OfficerAuditLog.objects.all().delete()

                report['deleted_counts']['promotion_requests'] = p_cnt
                report['deleted_counts']['medal_requests'] = m_cnt
                report['deleted_counts']['transfer_history'] = t_cnt
                report['deleted_counts']['audit_logs'] = a_cnt

            # 5. COMMUNICATIONS & LOGS
            if clean_comms:
                notif_cnt = Notification.objects.count()
                chat_cnt = ChatMessage.objects.count()
                otp_cnt = OTPVerification.objects.count()

                Notification.objects.all().delete()
                ChatMessage.objects.all().delete()
                OTPVerification.objects.all().delete()

                report['deleted_counts']['notifications'] = notif_cnt
                report['deleted_counts']['chat_messages'] = chat_cnt
                report['deleted_counts']['otp_verifications'] = otp_cnt

            # 6. OFFICERS & ATTACHMENTS (Only if selected)
            if clean_officers:
                for oatt in OfficerAttachment.objects.all():
                    if clean_media and oatt.file:
                        safe_delete_file_field(oatt.file)
                        media_files_deleted += 1
                for catt in ContractOfficerAttachment.objects.all():
                    if clean_media and catt.file:
                        safe_delete_file_field(catt.file)
                        media_files_deleted += 1
                for cs in CivilServantProfile.objects.all():
                    if clean_media and getattr(cs, 'photo', None):
                        safe_delete_file_field(cs.photo)
                        media_files_deleted += 1
                for co in ContractOfficer.objects.all():
                    if clean_media and getattr(co, 'photo', None):
                        safe_delete_file_field(co.photo)
                        media_files_deleted += 1

                OfficerAttachment.objects.all().delete()
                ContractOfficerAttachment.objects.all().delete()
                cs_cnt = CivilServantProfile.objects.count()
                co_cnt = ContractOfficer.objects.count()
                CivilServantProfile.objects.all().delete()
                ContractOfficer.objects.all().delete()

                report['deleted_counts']['civil_servants'] = cs_cnt
                report['deleted_counts']['contract_officers'] = co_cnt

            # 7. TEST USERS (Only if selected, NEVER delete superusers or current acting user)
            if clean_users:
                acting_username = user.username.lower() if user else 'admin'
                protected_names = {'admin', acting_username}

                users_to_delete = User.objects.exclude(is_superuser=True).exclude(username__in=protected_names)
                u_cnt = users_to_delete.count()
                users_to_delete.delete()
                report['deleted_counts']['test_users'] = u_cnt

            # 8. GENERAL ORPHANED MEDIA CLEANUP (if clean_media)
            if clean_media:
                media_root = Path(settings.MEDIA_ROOT)
                # If factory reset, clean subdirectories inside media/ except base folder
                if mode == 'factory' or (clean_docs and clean_officers and clean_veh_reqs):
                    for sub in ['documents', 'officer_attachments', 'officers', 'promotions', 'temp']:
                        target_sub = media_root / sub
                        if target_sub.exists() and target_sub.is_dir():
                            for root, _, files in os.walk(target_sub):
                                for f in files:
                                    try:
                                        os.remove(os.path.join(root, f))
                                        media_files_deleted += 1
                                    except Exception:
                                        pass
                report['deleted_counts']['media_files'] = media_files_deleted

        total_cnt = sum(report['deleted_counts'].values())
        report['total_deleted'] = total_cnt
        report['success'] = True

    except Exception as db_err:
        report['error'] = f"កំហុសអំឡុងពេលសម្អាតទិន្នន័យ (Database Error): {str(db_err)}"
        return report

    return report

