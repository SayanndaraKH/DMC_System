import os
import json
import socket
from pathlib import Path
from datetime import datetime

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings

from .backup_service import (
    get_system_stats,
    create_full_backup,
    create_db_backup,
    create_media_backup,
    create_safety_snapshot,
    restore_backup,
    inspect_backup_file,
    list_local_backups,
    BACKUP_DIR,
)
from .sync_service import (
    ping_server,
    push_to_server,
    pull_from_server,
    bidirectional_sync,
    get_default_sync_token,
)


def get_lan_ip_addresses():
    """
    Detects active LAN / Wi-Fi IP addresses of the host machine.
    """
    ips = []
    # Method 1: Connect UDP to discover default routing interface IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip and not primary_ip.startswith('127.'):
            ips.append(primary_ip)
    except Exception:
        pass

    # Method 2: Inspect host addrinfo
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ':' not in ip and not ip.startswith('127.') and ip not in ips:
                if not ip.startswith('169.254.'):  # ignore APIPA fallback
                    ips.append(ip)
    except Exception:
        pass

    if not ips:
        ips.append('127.0.0.1')
    return ips


def verify_sync_token(request):
    """
    Validates sync authentication token from Authorization Bearer header or query param.
    """
    expected_token = get_default_sync_token()
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
    elif 'X-Sync-Token' in request.headers:
        token = request.headers.get('X-Sync-Token', '').strip()
    elif 'token' in request.GET:
        token = request.GET.get('token', '').strip()

    return token and token == expected_token


# ==============================================================================
# USER & ADMIN UI DASHBOARD VIEWS
# ==============================================================================

@login_required
def backup_sync_dashboard(request):
    """
    Main Backup, Restore, and Synchronization Center.
    Accessible to logged-in users to freely download backups,
    and for Admins to perform restores and trigger sync.
    """
    stats = get_system_stats()
    local_backups = list_local_backups()
    lan_ips = get_lan_ip_addresses()
    primary_lan_ip = lan_ips[0] if lan_ips else '127.0.0.1'
    lan_port = getattr(settings, 'SERVER_PORT', 8000)
    lan_url = f"http://{primary_lan_ip}:{lan_port}"

    is_admin_user = (
        request.user.is_superuser or 
        request.user.username.upper() == 'ADMIN' or
        getattr(getattr(request.user, 'profile', None), 'is_admin', False) or
        getattr(getattr(request.user, 'profile', None), 'is_leadership', False)
    )

    default_sync_token = get_default_sync_token()

    context = {
        'stats': stats,
        'local_backups': local_backups,
        'lan_ips': lan_ips,
        'primary_lan_ip': primary_lan_ip,
        'lan_url': lan_url,
        'is_admin_user': is_admin_user,
        'default_sync_token': default_sync_token,
        'page_title': 'មជ្ឈមណ្ឌល Backup & សមកាលកម្មទិន្នន័យ (Backup & Sync Center)',
    }
    return render(request, 'dms/backup_sync.html', context)


@login_required
def download_full_backup(request):
    """
    Creates and streams the complete system backup (.zip containing data.json + media/ + manifest.json)
    directly to the user's browser.
    """
    try:
        user_note = f"Downloaded by {request.user.get_full_name() or request.user.username}"
        backup_res = create_full_backup(user=request.user, note=user_note)
        if not backup_res.get('success'):
            messages.error(request, f"កំហុសក្នុងការបង្កើត Backup: {backup_res.get('error')}")
            return redirect('backup_sync_dashboard')

        file_path = backup_res['file_path']
        filename = backup_res['filename']

        response = FileResponse(
            open(file_path, 'rb'),
            content_type='application/zip',
            as_attachment=True,
            filename=filename
        )
        return response
    except Exception as e:
        messages.error(request, f"បរាជ័យក្នុងការទាញយក Backup: {str(e)}")
        return redirect('backup_sync_dashboard')


@login_required
def download_db_backup(request):
    """
    Streams lightweight database-only backup (.zip containing data.json + manifest.json).
    """
    try:
        user_note = f"DB Backup downloaded by {request.user.username}"
        backup_res = create_db_backup(user=request.user, note=user_note)
        file_path = backup_res['file_path']
        filename = backup_res['filename']

        return FileResponse(
            open(file_path, 'rb'),
            content_type='application/zip',
            as_attachment=True,
            filename=filename
        )
    except Exception as e:
        messages.error(request, f"បរាជ័យក្នុងការទាញយក Database Backup: {str(e)}")
        return redirect('backup_sync_dashboard')


@login_required
def download_media_backup(request):
    """
    Streams media attachments backup (.zip containing all media/ files).
    """
    try:
        user_note = f"Media Backup downloaded by {request.user.username}"
        backup_res = create_media_backup(user=request.user, note=user_note)
        file_path = backup_res['file_path']
        filename = backup_res['filename']

        return FileResponse(
            open(file_path, 'rb'),
            content_type='application/zip',
            as_attachment=True,
            filename=filename
        )
    except Exception as e:
        messages.error(request, f"បរាជ័យក្នុងការទាញយក Media Backup: {str(e)}")
        return redirect('backup_sync_dashboard')


@login_required
def download_local_backup_file(request, filename):
    """
    Allows downloading an existing saved backup from the local server's backups/ directory.
    """
    # Prevent path traversal
    safe_name = os.path.basename(filename)
    target_file = BACKUP_DIR / safe_name

    if not target_file.exists() or not target_file.is_file():
        raise Http404("Backup file not found")

    return FileResponse(
        open(target_file, 'rb'),
        content_type='application/zip',
        as_attachment=True,
        filename=safe_name
    )


@login_required
def delete_local_backup_file(request, filename):
    """
    Deletes an existing saved backup from the local server's backups/ directory.
    """
    if not (request.user.is_superuser or request.user.username.upper() == 'ADMIN'):
        messages.error(request, "លោកអ្នកគ្មានសិទ្ធិលុបឯកសារ Backup ឡើយ។")
        return redirect('backup_sync_dashboard')

    safe_name = os.path.basename(filename)
    target_file = BACKUP_DIR / safe_name

    if target_file.exists() and target_file.is_file():
        try:
            os.remove(target_file)
            messages.success(request, f"បានលុបឯកសារ Backup {safe_name} ដោយជោគជ័យ។")
        except Exception as e:
            messages.error(request, f"មិនអាចលុបឯកសារបានឡើយ: {str(e)}")
    else:
        messages.warning(request, "រកមិនឃើញឯកសារ Backup នោះឡើយ។")

    return redirect('backup_sync_dashboard')


@login_required
def create_local_snapshot_action(request):
    """
    One-click action to create and save a fresh full backup snapshot directly into the server's backups/ directory.
    """
    if request.method == 'POST':
        try:
            res = create_full_backup(user=request.user, note="Local Server Snapshot created via Web UI")
            if res.get('success'):
                messages.success(
                    request,
                    f"✅ បានបង្កើត Snapshot បម្រុងទុកជោគជ័យ៖ {res['filename']} (ទំហំ {res['file_size_mb']} MB)"
                )
            else:
                messages.error(request, f"បរាជ័យក្នុងការបង្កើត Snapshot: {res.get('error')}")
        except Exception as e:
            messages.error(request, f"កំហុសប្រព័ន្ធ: {str(e)}")
    return redirect('backup_sync_dashboard')


@login_required
def restore_backup_action(request):
    """
    Handles uploaded backup package (.zip or .json) and restores data.
    """
    if request.method != 'POST':
        return redirect('backup_sync_dashboard')

    if not (request.user.is_superuser or request.user.username.upper() == 'ADMIN'):
        messages.error(request, "លោកអ្នកគ្មានសិទ្ធិបញ្ចូលទិន្នន័យត្រឡប់មកវិញ (Restore) ឡើយ។ មុខងារនេះសម្រាប់តែ Admin ប៉ុណ្ណោះ។")
        return redirect('backup_sync_dashboard')

    uploaded_file = request.FILES.get('backup_file')
    if not uploaded_file:
        messages.warning(request, "សូមជ្រើសរើសឯកសារ Backup (.zip ឬ .json) ជាមុនសិន។")
        return redirect('backup_sync_dashboard')

    restore_mode = request.POST.get('restore_mode', 'merge')
    if restore_mode not in ['merge', 'replace']:
        restore_mode = 'merge'

    try:
        result = restore_backup(uploaded_file, mode=restore_mode)
        if result.get('success'):
            mode_text = "សមកាលកម្មបញ្ចូលគ្នា (Smart Merge - Lossless)" if restore_mode == 'merge' else "ស្តារឡើងវិញទាំងស្រុង (Full Replace)"
            created = result.get('records_created', 0)
            updated = result.get('records_updated', 0)
            media = result.get('media_restored', 0)
            safety = os.path.basename(result.get('safety_snapshot', ''))

            msg = (
                f"🎉 ការស្តារទិន្នន័យ ({mode_text}) សម្រេចបានជោគជ័យ! "
                f"បញ្ចូលថ្មី: {created} records, កែប្រែ: {updated} records, "
                f"ឯកសារ Media ស្តារបាន: {media} files។ "
                f"(ប្រព័ន្ធបានរក្សាទុក Safety Snapshot ជាមុន៖ {safety})"
            )
            messages.success(request, msg)
        else:
            messages.error(request, f"❌ ការស្តារទិន្នន័យបានបរាជ័យ៖ {result.get('error')}")
    except Exception as e:
        messages.error(request, f"❌ កំហុសបច្ចេកទេសក្នុងពេល Restore: {str(e)}")

    return redirect('backup_sync_dashboard')


# ==============================================================================
# AJAX CLIENT SYNC API (Triggers client-to-server operations from Dashboard UI)
# ==============================================================================

@login_required
def api_test_server_connection(request):
    """
    AJAX endpoint to test connection to remote/central server.
    """
    server_url = request.GET.get('server_url', '').strip()
    token = request.GET.get('token', '').strip() or None

    if not server_url:
        return JsonResponse({'online': False, 'error': 'សូមបញ្ចូល Server URL ជាមុនសិន។'})

    result = ping_server(server_url, token=token)
    return JsonResponse(result)


@login_required
def api_trigger_sync(request):
    """
    AJAX endpoint to trigger push, pull, or 2-way sync.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    server_url = data.get('server_url', '').strip()
    token = data.get('token', '').strip() or None
    sync_action = data.get('action', 'bidirectional')

    if not server_url:
        return JsonResponse({'success': False, 'error': 'សូមបញ្ចូលអាសយដ្ឋាន Server URL!'})

    if sync_action == 'ping':
        res = ping_server(server_url, token)
        return JsonResponse(res)

    elif sync_action == 'push':
        res = push_to_server(server_url, token=token, user=request.user)
        return JsonResponse(res)

    elif sync_action == 'pull':
        res = pull_from_server(server_url, token=token, user=request.user)
        return JsonResponse(res)

    elif sync_action == 'bidirectional':
        res = bidirectional_sync(server_url, token=token, user=request.user)
        return JsonResponse(res)

    else:
        return JsonResponse({'success': False, 'error': f"Unknown action: {sync_action}"})


# ==============================================================================
# SERVER-SIDE SYNC ENDPOINTS (For incoming sync calls from other PCs or clients)
# ==============================================================================

@csrf_exempt
def api_sync_ping(request):
    """
    Public health/ping endpoint for sync clients with token authentication.
    """
    if not verify_sync_token(request):
        return JsonResponse({'error': 'Unauthorized. Invalid or missing Sync Token.'}, status=401)

    stats = get_system_stats()
    return JsonResponse({
        'status': 'OK',
        'system_name': 'DMS Cambodia Central Server',
        'server_time': datetime.now().isoformat(),
        'stats': stats,
    })


@csrf_exempt
def api_sync_export(request):
    """
    Generates and streams full sync package to an authorized requesting client (Pull sync).
    """
    if not verify_sync_token(request):
        return JsonResponse({'error': 'Unauthorized. Invalid or missing Sync Token.'}, status=401)

    try:
        backup_res = create_full_backup(user=None, note="Exported via Remote Sync API (Pull)")
        if not backup_res.get('success'):
            return JsonResponse({'error': f"Export failed: {backup_res.get('error')}"}, status=500)

        file_path = backup_res['file_path']
        filename = backup_res['filename']

        return FileResponse(
            open(file_path, 'rb'),
            content_type='application/zip',
            as_attachment=True,
            filename=filename
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_sync_receive(request):
    """
    Receives uploaded sync package from a client and performs a lossless Smart Merge (Push sync).
    """
    if not verify_sync_token(request):
        return JsonResponse({'error': 'Unauthorized. Invalid or missing Sync Token.'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    uploaded_file = request.FILES.get('sync_file')
    if not uploaded_file:
        return JsonResponse({'error': 'No sync_file attached.'}, status=400)

    try:
        # Perform lossless merge
        result = restore_backup(uploaded_file, mode='merge')
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
