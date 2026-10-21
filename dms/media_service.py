import os
import sys
import logging
import mimetypes
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse, Http404
from django.views.static import serve

logger = logging.getLogger(__name__)

# Primary GitHub repository for remote media fallback
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/SayanndaraKH/DMC_System/main/media"

# Clean SVG fallback avatar for officers when photo is completely missing or offline
DEFAULT_AVATAR_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="100%" height="100%">
  <rect width="120" height="120" fill="#e2e8f0" rx="60"/>
  <circle cx="60" cy="46" r="24" fill="#94a3b8"/>
  <path d="M24 104 C24 82, 42 76, 60 76 C78 76, 96 82, 96 104 Z" fill="#94a3b8"/>
</svg>"""


def get_candidate_media_roots():
    """
    Returns an ordered list of directory Paths where media files may exist on the local machine.
    """
    roots = []
    
    # 1. Primary configured MEDIA_ROOT
    if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
        roots.append(Path(settings.MEDIA_ROOT).resolve())
        
    # 2. Frozen PyInstaller locations
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).resolve().parent
        roots.append((exe_dir / 'media').resolve())
        roots.append((exe_dir.parent / 'media').resolve())
        
        # PyInstaller bundled temporary folder
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            roots.append((Path(meipass) / 'media').resolve())

    # 3. Project BASE_DIR
    if hasattr(settings, 'BASE_DIR') and settings.BASE_DIR:
        roots.append((Path(settings.BASE_DIR) / 'media').resolve())

    # 4. Standard Windows LocalAppData folder
    local_app = os.environ.get('LOCALAPPDATA', '')
    if local_app:
        roots.append((Path(local_app) / 'DMC_System' / 'media').resolve())

    # Deduplicate while preserving order
    seen = set()
    unique_roots = []
    for r in roots:
        r_str = str(r).lower()
        if r_str not in seen:
            seen.add(r_str)
            unique_roots.append(r)

    return unique_roots


def get_lan_server_url():
    """
    Reads central LAN server URL from dmc_config.txt if configured and not pointing to localhost.
    """
    try:
        base_dir = getattr(settings, 'BASE_DIR', Path(__file__).resolve().parent.parent)
        cfg_file = Path(base_dir) / 'dmc_config.txt'
        if not cfg_file.exists() and getattr(sys, 'frozen', False):
            cfg_file = Path(sys.executable).resolve().parent / 'dmc_config.txt'
            
        if cfg_file.exists():
            with open(cfg_file, 'r', encoding='utf-8') as f:
                url = f.read().strip()
                if url.startswith('http') and '127.0.0.1' not in url and 'localhost' not in url:
                    return url.rstrip('/')
    except Exception:
        pass
    return None


def download_remote_media_file(rel_path, target_abs_path, timeout=15):
    """
    Downloads a media file from GitHub Raw (or central LAN server) and saves it locally.
    """
    # Quote individual path segments for safe URL formatting (especially Khmer unicode)
    clean_rel = rel_path.replace('\\', '/').lstrip('/')
    quoted_rel = '/'.join(urllib.parse.quote(seg) for seg in clean_rel.split('/'))
    
    candidate_urls = []
    
    # 1. Central LAN server if configured
    lan_url = get_lan_server_url()
    if lan_url:
        candidate_urls.append(f"{lan_url}/media/{quoted_rel}")
        
    # 2. GitHub Raw official repository
    candidate_urls.append(f"{GITHUB_RAW_BASE}/{quoted_rel}")

    headers = {
        'User-Agent': 'DMC-MediaSync/1.0 (Windows; Khmer HR System)'
    }

    for url in candidate_urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if data:
                        target_abs_path.parent.mkdir(parents=True, exist_ok=True)
                        tmp_file = target_abs_path.with_suffix(target_abs_path.suffix + f'.tmp_{os.getpid()}')
                        with open(tmp_file, 'wb') as f:
                            f.write(data)
                        if tmp_file.exists():
                            if target_abs_path.exists():
                                try:
                                    target_abs_path.unlink()
                                except OSError:
                                    pass
                            tmp_file.replace(target_abs_path)
                            logger.info(f"Successfully downloaded and cached media: {clean_rel} from {url}")
                            return True
        except Exception as e:
            logger.debug(f"Media fetch failed from {url}: {e}")
            continue

    return False


def fetch_media_from_neon_cloud(rel_path, target_dest):
    """
    Retrieves the binary content of a media file directly from the Neon Cloud PostgreSQL Database
    and writes it to target_dest on the local disk (serving as a persistent local cache).
    """
    clean_rel = str(rel_path).replace('\\', '/').lstrip('/')
    if not clean_rel:
        return False

    try:
        from dms.models import CloudMediaStorage
        # 1. Exact match
        record = CloudMediaStorage.objects.filter(file_path=clean_rel).first()
        # 2. Case-insensitive match
        if not record:
            record = CloudMediaStorage.objects.filter(file_path__iexact=clean_rel).first()
        # 3. Filename match fallback
        if not record:
            fname = os.path.basename(clean_rel)
            record = CloudMediaStorage.objects.filter(file_name=fname).first()

        if record and record.file_data:
            target_dest.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = target_dest.with_suffix(target_dest.suffix + f'.tmp_{os.getpid()}_{threading.get_ident()}')
            raw_bytes = bytes(record.file_data)
            with open(tmp_file, 'wb') as f:
                f.write(raw_bytes)
            if tmp_file.exists():
                if target_dest.exists():
                    try:
                        target_dest.unlink()
                    except OSError:
                        pass
                tmp_file.replace(target_dest)
                logger.info(f"Loaded and cached media from Neon Cloud DB: {clean_rel} ({len(raw_bytes)} bytes)")
                return True
    except Exception as e:
        logger.warning(f"Neon Cloud media lookup failed for {clean_rel}: {e}")

    return False


def save_media_to_neon_cloud(rel_path, data=None, local_abs_path=None):
    """
    Uploads or updates a media file in the Neon Cloud Database.
    Accepts either raw bytes `data` or local file path `local_abs_path`.
    """
    clean_rel = str(rel_path).replace('\\', '/').lstrip('/')
    if not clean_rel:
        return False

    try:
        from dms.models import CloudMediaStorage
        if data is None and local_abs_path and os.path.exists(local_abs_path):
            with open(local_abs_path, 'rb') as f:
                data = f.read()

        if not data:
            return False

        content_type, _ = mimetypes.guess_type(clean_rel)
        if not content_type:
            ext = os.path.splitext(clean_rel)[1].lower()
            if ext == '.pdf':
                content_type = 'application/pdf'
            elif ext in ['.jpg', '.jpeg']:
                content_type = 'image/jpeg'
            elif ext == '.png':
                content_type = 'image/png'
            elif ext == '.webp':
                content_type = 'image/webp'
            else:
                content_type = 'application/octet-stream'

        fname = os.path.basename(clean_rel)
        CloudMediaStorage.objects.update_or_create(
            file_path=clean_rel,
            defaults={
                'file_name': fname,
                'content_type': content_type,
                'file_size': len(data),
                'file_data': data,
            }
        )
        logger.info(f"Saved media to Neon Cloud DB: {clean_rel} ({len(data)} bytes)")
        return True
    except Exception as e:
        logger.error(f"Failed to save {clean_rel} to Neon Cloud DB: {e}")
        return False


def sync_field_file_to_neon_async(field_file):
    """
    Saves a Django FieldFile/ImageField to Neon Cloud DB in a background thread.
    """
    if not field_file or not hasattr(field_file, 'name') or not field_file.name:
        return

    rel_name = str(field_file.name)

    def _task():
        try:
            from django.db import close_old_connections
            close_old_connections()
            abs_path = resolve_media_path(rel_name, auto_download=False)
            if abs_path and os.path.isfile(abs_path):
                save_media_to_neon_cloud(rel_name, local_abs_path=abs_path)
            elif hasattr(field_file, 'file') and field_file.file:
                field_file.file.seek(0)
                data = field_file.file.read()
                save_media_to_neon_cloud(rel_name, data=data)
        except Exception as e:
            logger.debug(f"Async Neon DB upload notice for {rel_name}: {e}")
        finally:
            try:
                from django.db import close_old_connections
                close_old_connections()
            except Exception:
                pass

    threading.Thread(target=_task, daemon=True).start()


def resolve_media_path(rel_path_or_field, auto_download=True, timeout=20):
    """
    Finds the absolute path of a media file.
    1. Looks in local candidate directories (instant cache hit).
    2. If missing locally, fetches from Neon Cloud Database (primary cloud source).
    3. If not found in Neon DB, falls back to GitHub Raw / Central LAN.
    """
    if not rel_path_or_field:
        return None

    # Handle Django FieldFile/FileField or string path
    if hasattr(rel_path_or_field, 'name'):
        rel_str = str(rel_path_or_field.name)
    else:
        rel_str = str(rel_path_or_field)

    # Normalize path and decode URL quoting if present
    rel_str = urllib.parse.unquote(rel_str).replace('\\', '/').lstrip('/')
    if not rel_str or '..' in rel_str:
        return None

    candidate_roots = get_candidate_media_roots()
    primary_root = candidate_roots[0] if candidate_roots else Path(settings.MEDIA_ROOT).resolve()

    # Step 1: Check candidate local directories
    for root in candidate_roots:
        candidate_file = (root / rel_str).resolve()
        if candidate_file.is_file():
            # If found in secondary folder, ensure cached in primary MEDIA_ROOT
            if candidate_file != (primary_root / rel_str).resolve():
                try:
                    target_file = (primary_root / rel_str).resolve()
                    if not target_file.exists():
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        import shutil
                        shutil.copy2(candidate_file, target_file)
                        return str(target_file)
                except Exception:
                    pass
            return str(candidate_file)

    # Step 2: Not found locally -> Fetch from Neon Cloud Database (Instant & Cloud-Synced)
    target_dest = (primary_root / rel_str).resolve()
    if auto_download:
        if fetch_media_from_neon_cloud(rel_str, target_dest):
            if target_dest.is_file():
                return str(target_dest)

        # Step 3: Fallback to GitHub / Central LAN
        if download_remote_media_file(rel_str, target_dest, timeout=timeout):
            if target_dest.is_file():
                # Also save to Neon Cloud DB so subsequent queries are ultra-fast from DB
                threading.Thread(
                    target=save_media_to_neon_cloud,
                    args=(rel_str,),
                    kwargs={'local_abs_path': str(target_dest)},
                    daemon=True
                ).start()
                return str(target_dest)

    return None


def smart_serve_media(request, path):
    """
    Custom Django view for serving /media/<path> requests with:
    - Multi-folder resolution
    - Automatic remote download & caching from GitHub/LAN
    - Range request support for PDF viewer
    - Clean SVG avatar fallback for missing pictures
    """
    clean_path = urllib.parse.unquote(path).replace('\\', '/').lstrip('/')
    real_path = resolve_media_path(clean_path, auto_download=True)

    if real_path and os.path.isfile(real_path):
        parent_dir = os.path.dirname(real_path)
        filename = os.path.basename(real_path)
        # Use django.views.static.serve for correct HTTP 206 Partial Content / Range support
        response = serve(request, filename, document_root=parent_dir)
        response['Access-Control-Allow-Origin'] = '*'
        response['Cache-Control'] = 'public, max-age=86400'
        return response

    # If the missing file was an avatar image, return a default SVG avatar instead of 404
    ext = os.path.splitext(clean_path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
        resp = HttpResponse(DEFAULT_AVATAR_SVG, content_type='image/svg+xml')
        resp['Cache-Control'] = 'public, max-age=3600'
        return resp

    raise Http404("File ឯកសារមិនត្រូវបានរកឃើញឡើយ!")


_sync_started = False

def sync_officer_photos_async():
    """
    Runs in a background thread to pre-fetch civil servant photos
    so that all pictures are cached and load instantly.
    """
    global _sync_started
    if _sync_started:
        return
    _sync_started = True

    def _worker():
        try:
            import time
            time.sleep(2)  # Wait for DB connection & startup to settle
            from dms.models import CivilServantProfile, ContractOfficer

            profiles = list(CivilServantProfile.objects.exclude(photo='').values_list('photo', flat=True))
            contract_photos = list(ContractOfficer.objects.exclude(photo='').values_list('photo', flat=True))
            all_photos = profiles + contract_photos

            downloaded_count = 0
            for photo_name in all_photos:
                if photo_name:
                    p = resolve_media_path(photo_name, auto_download=True, timeout=8)
                    if p:
                        downloaded_count += 1
            if downloaded_count > 0:
                logger.info(f"Background media sync completed: {downloaded_count} photos verified/cached.")
        except Exception as e:
            logger.debug(f"Async media sync notice: {e}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
