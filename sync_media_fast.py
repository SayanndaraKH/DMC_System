import os
import sys
import time
import mimetypes
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dms_project.settings')
import django
django.setup()

from django.db import connection, close_old_connections
from dms.models import CloudMediaStorage

def get_mime(path):
    content_type, _ = mimetypes.guess_type(str(path))
    if not content_type:
        ext = path.suffix.lower()
        if ext == '.pdf':
            return 'application/pdf'
        elif ext in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        elif ext == '.png':
            return 'image/png'
        elif ext == '.webp':
            return 'image/webp'
        elif ext in ['.doc', '.docx']:
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif ext in ['.xls', '.xlsx']:
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return 'application/octet-stream'
    return content_type

def upload_single_file(item):
    abs_path, clean_rel, file_size = item
    close_old_connections()
    try:
        with open(abs_path, 'rb') as f:
            data = f.read()

        ct = get_mime(abs_path)
        CloudMediaStorage.objects.update_or_create(
            file_path=clean_rel,
            defaults={
                'file_name': abs_path.name,
                'content_type': ct,
                'file_size': file_size,
                'file_data': data,
            }
        )
        return True, clean_rel, file_size, None
    except Exception as e:
        return False, clean_rel, file_size, str(e)
    finally:
        close_old_connections()

def main():
    from django.conf import settings
    media_dir = Path(settings.MEDIA_ROOT).resolve()
    if not media_dir.exists():
        media_dir = (Path(__file__).resolve().parent / 'media').resolve()

    print(f"Scanning media: {media_dir}", flush=True)
    all_items = []
    total_bytes = 0
    for root, dirs, files in os.walk(media_dir):
        for f in files:
            p = Path(root) / f
            sz = p.stat().st_size
            total_bytes += sz
            rel = p.relative_to(media_dir).as_posix().lstrip('/')
            all_items.append((p, rel, sz))

    print(f"Total files on disk: {len(all_items)} ({total_bytes / (1024*1024):.2f} MB)", flush=True)

    print("Checking already uploaded records in Neon Cloud DB...", flush=True)
    existing = dict(CloudMediaStorage.objects.values_list('file_path', 'file_size'))
    print(f"Found {len(existing)} existing records in Neon DB.", flush=True)

    to_upload = [item for item in all_items if item[1] not in existing or existing[item[1]] != item[2]]
    print(f"Files to upload: {len(to_upload)}", flush=True)

    if not to_upload:
        print("ALL MEDIA FILES ARE ALREADY FULLY SYNCED TO NEON CLOUD DB!", flush=True)
        return

    start_time = time.time()
    uploaded_count = 0
    uploaded_bytes = 0
    error_count = 0

    max_workers = 8
    print(f"Starting parallel upload using {max_workers} worker threads...", flush=True)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(upload_single_file, item): item for item in to_upload}
        for future in as_completed(futures):
            success, rel_name, sz, err = future.result()
            if success:
                uploaded_count += 1
                uploaded_bytes += sz
                pct = (uploaded_count / len(to_upload)) * 100
                print(f"[{uploaded_count}/{len(to_upload)}] ({pct:.1f}%) OK: {rel_name} ({sz/1024:.1f} KB)", flush=True)
            else:
                error_count += 1
                print(f"[FAIL] {rel_name}: {err}", flush=True)

    elapsed = time.time() - start_time
    print("="*60, flush=True)
    print(f"FAST SYNC COMPLETE in {elapsed:.1f} seconds!", flush=True)
    print(f"Uploaded: {uploaded_count} files ({uploaded_bytes / (1024*1024):.2f} MB)", flush=True)
    print(f"Skipped: {len(all_items) - len(to_upload)} files", flush=True)
    print(f"Errors: {error_count}", flush=True)
    print("="*60, flush=True)

if __name__ == '__main__':
    main()
