import os
import sys
import time
import mimetypes
from pathlib import Path

# Force UTF-8 stdout
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dms_project.settings')
import django
django.setup()

from django.db import transaction, connection
from dms.models import CloudMediaStorage

def sync_all_media():
    from django.conf import settings
    media_dir = Path(settings.MEDIA_ROOT).resolve()
    if not media_dir.exists():
        media_dir = (Path(__file__).resolve().parent / 'media').resolve()
    
    print(f"Scanning media directory: {media_dir}")
    all_files = []
    total_bytes = 0
    for root, dirs, files in os.walk(media_dir):
        for f in files:
            p = Path(root) / f
            sz = p.stat().st_size
            total_bytes += sz
            rel = p.relative_to(media_dir).as_posix()
            all_files.append((p, rel, sz))

    print(f"Total files found: {len(all_files)} ({total_bytes / (1024*1024):.2f} MB)")

    # Fetch existing files in Neon DB (file_path and file_size)
    print("Checking existing records in Neon Cloud DB...")
    existing = dict(CloudMediaStorage.objects.values_list('file_path', 'file_size'))
    print(f"Already in Neon Cloud DB: {len(existing)} files")

    uploaded = 0
    skipped = 0
    errors = 0
    bytes_uploaded = 0

    for idx, (abs_path, rel_path, file_size) in enumerate(all_files, 1):
        # Normalize rel_path
        clean_rel = rel_path.lstrip('/')
        
        # If already exists with exact same size, skip
        if clean_rel in existing and existing[clean_rel] == file_size:
            skipped += 1
            if idx % 50 == 0 or idx == len(all_files):
                print(f"[{idx}/{len(all_files)}] Progress: {idx/len(all_files)*100:.1f}% (Uploaded: {uploaded}, Skipped: {skipped})")
            continue

        try:
            with open(abs_path, 'rb') as f:
                data = f.read()

            content_type, _ = mimetypes.guess_type(str(abs_path))
            if not content_type:
                ext = abs_path.suffix.lower()
                if ext == '.pdf':
                    content_type = 'application/pdf'
                elif ext in ['.jpg', '.jpeg']:
                    content_type = 'image/jpeg'
                elif ext == '.png':
                    content_type = 'image/png'
                elif ext == '.webp':
                    content_type = 'image/webp'
                elif ext in ['.doc', '.docx']:
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif ext in ['.xls', '.xlsx']:
                    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                else:
                    content_type = 'application/octet-stream'

            CloudMediaStorage.objects.update_or_create(
                file_path=clean_rel,
                defaults={
                    'file_name': abs_path.name,
                    'content_type': content_type,
                    'file_size': file_size,
                    'file_data': data,
                }
            )
            uploaded += 1
            bytes_uploaded += file_size
            print(f"[{idx}/{len(all_files)}] ({(idx/len(all_files))*100:.1f}%) Uploaded: {clean_rel} ({file_size / 1024:.1f} KB)")
        except Exception as e:
            errors += 1
            print(f"[{idx}/{len(all_files)}] ERROR uploading {clean_rel}: {e}")
            time.sleep(1)

    print("\n" + "="*60)
    print("SYNC COMPLETE!")
    print(f"Uploaded: {uploaded} files ({bytes_uploaded / (1024*1024):.2f} MB)")
    print(f"Skipped (already up to date): {skipped} files")
    print(f"Errors: {errors}")
    print("="*60)

if __name__ == '__main__':
    sync_all_media()
