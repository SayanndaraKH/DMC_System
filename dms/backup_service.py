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
    Uses in-memory StringIO with explicit UTF-8 to prevent Windows CP1252 charmap errors.
    """
    buf = io.StringIO()
    # Filter only models that currently exist in apps
    valid_apps_models = []
    for m_str in MODELS_TO_BACKUP:
        app_label, model_name = m_str.split('.')
        try:
            apps.get_model(app_label, model_name)
            valid_apps_models.append(m_str)
        except LookupError:
            pass

    call_command(
        'dumpdata',
        *valid_apps_models,
        natural_foreign=True,
        natural_primary=True,
        exclude=['contenttypes', 'sessions'],
        indent=2,
        stdout=buf
    )
    return buf.getvalue()


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
            with transaction.atomic():
                # If replace mode, we clear existing application tables in reverse order
                if mode == 'replace':
                    # Reverse dependency cleanup
                    models_to_clear = list(reversed(MODELS_TO_BACKUP))
                    for m_str in models_to_clear:
                        app_label, model_name = m_str.split('.')
                        try:
                            m_cls = apps.get_model(app_label, model_name)
                            if m_str == 'auth.User':
                                # Keep superusers / ADMIN if needed, or clear non-superusers
                                m_cls.objects.exclude(is_superuser=True).delete()
                            else:
                                m_cls.objects.all().delete()
                        except Exception:
                            pass

                # Deserialize objects
                deserialized_objects = list(serializers.deserialize('json', json_str, ignorenonexistent=True))
                
                # Sort objects by MODELS_TO_BACKUP order so foreign keys are satisfied
                order_map = {m_str.lower(): idx for idx, m_str in enumerate(MODELS_TO_BACKUP)}
                def sort_key(d_obj):
                    key = f"{d_obj.object._meta.app_label}.{d_obj.object._meta.model_name}".lower()
                    return order_map.get(key, 999)

                deserialized_objects.sort(key=sort_key)

                for d_obj in deserialized_objects:
                    m_cls = d_obj.object.__class__
                    pk_val = d_obj.object.pk
                    exists = False
                    if pk_val:
                        try:
                            exists = m_cls.objects.filter(pk=pk_val).exists()
                        except Exception:
                            exists = False

                    try:
                        # In merge mode, if it exists, obj.save() performs an update; if not, an insert
                        d_obj.save()
                        if exists:
                            report['records_updated'] += 1
                        else:
                            report['records_created'] += 1
                    except Exception as save_err:
                        report['records_skipped'] += 1
                        report['details'].append(f"Skipped {m_cls.__name__} (pk={pk_val}): {str(save_err)}")

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
                'is_safety_snapshot': item.name.startswith('safety_pre_restore_'),
            })

    backups.sort(key=lambda x: x['created_at'], reverse=True)
    return backups
