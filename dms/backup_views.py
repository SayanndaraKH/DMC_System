import os
import json
import socket
from pathlib import Path
from datetime import datetime
from functools import wraps

from django.shortcuts import render, redirect
from django.urls import reverse
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
    clean_system_data,
    get_clean_preview_counts,
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


def admin_only_required(view_func):
    """
    Decorator strictly enforcing that only UserAccount: ADMIN (or superuser)
    can access the Data Center, create/download backups, restore data, trigger sync,
    or manage snapshots.
    All other users are blocked and redirected to the dashboard with an alert message.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        is_admin = (
            request.user.is_superuser or
            (request.user.username and request.user.username.strip().upper() == 'ADMIN')
        )

        if not is_admin:
            is_ajax = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest' or
                'application/json' in request.headers.get('Accept', '') or
                request.path.startswith('/api/') or
                view_func.__name__.startswith('api_')
            )
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': 'សិទ្ធិត្រូវបានបដិសេធ៖ មុខងារមជ្ឈមណ្ឌលទិន្នន័យ (Data Center & Backup) ត្រូវបានអនុញ្ញាតសម្រាប់តែ UserAccount: ADMIN ប៉ុណ្ណោះ!'
                }, status=403)

            messages.error(
                request,
                '⛔ សិទ្ធិត្រូវបានបដិសេធ៖ មុខងារមជ្ឈមណ្ឌលទិន្នន័យ (Data Center & Backup) ត្រូវបានអនុញ្ញាតសម្រាប់តែ UserAccount: ADMIN ប៉ុណ្ណោះ!'
            )
            return redirect('dashboard')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ==============================================================================
# USER & ADMIN UI DASHBOARD VIEWS
# ==============================================================================

@admin_only_required
def backup_sync_dashboard(request):
    """
    Main Backup, Restore, and Synchronization Center (Data Center).
    Restricted strictly to UserAccount: ADMIN.
    Connected directly to Neon Cloud Database.
    """
    stats = get_system_stats()
    local_backups = list_local_backups()
    lan_ips = get_lan_ip_addresses()
    primary_lan_ip = lan_ips[0] if lan_ips else '127.0.0.1'
    lan_port = getattr(settings, 'SERVER_PORT', 8000)
    lan_url = f"http://{primary_lan_ip}:{lan_port}"

    from django.db import connection
    db_engine = connection.vendor
    is_neon_cloud = (db_engine == 'postgresql')
    db_host = connection.settings_dict.get('HOST', 'Neon Cloud PostgreSQL')
    db_name = connection.settings_dict.get('NAME', 'neondb')
    db_user = connection.settings_dict.get('USER', 'neondb_owner')

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            db_connected = True
    except Exception:
        db_connected = False

    default_sync_token = get_default_sync_token()

    context = {
        'stats': stats,
        'local_backups': local_backups,
        'lan_ips': lan_ips,
        'primary_lan_ip': primary_lan_ip,
        'lan_url': lan_url,
        'is_admin_user': True,
        'default_sync_token': default_sync_token,
        'clean_preview_counts': get_clean_preview_counts(),
        'page_title': 'មជ្ឈមណ្ឌល Backup & សមកាលកម្មទិន្នន័យ (Data Center - Neon Cloud)',
        'is_neon_cloud': is_neon_cloud,
        'db_engine': 'Neon Cloud PostgreSQL' if is_neon_cloud else 'Local Database',
        'db_host': db_host,
        'db_name': db_name,
        'db_user': db_user,
        'db_connected': db_connected,
    }
    return render(request, 'dms/backup_sync.html', context)


@admin_only_required
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


@admin_only_required
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


@admin_only_required
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


@admin_only_required
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


@admin_only_required
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


@admin_only_required
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


@admin_only_required
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


@admin_only_required
def clean_system_data_action(request):
    """
    Action to purge operational test data or complete factory reset to prepare DMS for live operation.
    Requires superuser or ADMIN role.
    """
    if request.method != 'POST':
        return redirect('backup_sync_dashboard')

    if not (request.user.is_superuser or request.user.username.upper() == 'ADMIN'):
        messages.error(request, "❌ លោកអ្នកគ្មានសិទ្ធិសម្អាតទិន្នន័យប្រព័ន្ធឡើយ។ មុខងារនេះសម្រាប់តែ Admin កំពូល (Superuser) ប៉ុណ្ណោះ។")
        return redirect('backup_sync_dashboard')

    confirm_text = request.POST.get('confirm_text', '').strip()
    auto_submit = request.POST.get('auto_submit') == '1'
    if not auto_submit and confirm_text not in ['CONFIRM', 'RESET', 'លុបទិន្នន័យ', 'AUTO', 'AUTO_SUBMIT']:
        messages.error(
            request,
            "⚠️ ការសម្អាតត្រូវបានបដិសេធ៖ លោកអ្នកត្រូវវាយពាក្យ 'CONFIRM' ឬចុចប៊ូតុង Auto-Submit ដើម្បីបញ្ជាក់សុវត្ថិភាព។"
        )
        return redirect('backup_sync_dashboard')

    mode = request.POST.get('clean_mode', 'operational')
    custom_options = {
        'clean_documents': request.POST.get('opt_clean_documents') == 'on',
        'clean_attendance': request.POST.get('opt_clean_attendance') == 'on',
        'clean_vehicle_requests': request.POST.get('opt_clean_vehicle_requests') == 'on',
        'clean_vehicles': request.POST.get('opt_clean_vehicles') == 'on',
        'clean_hr_requests': request.POST.get('opt_clean_hr_requests') == 'on',
        'clean_comms_logs': request.POST.get('opt_clean_comms_logs') == 'on',
        'clean_officers': request.POST.get('opt_clean_officers') == 'on',
        'clean_test_users': request.POST.get('opt_clean_test_users') == 'on',
        'clean_media_files': request.POST.get('opt_clean_media_files') == 'on',
    }

    try:
        res = clean_system_data(options=custom_options, user=request.user, mode=mode)
        if res.get('success'):
            counts = res['deleted_counts']
            if mode == 'test_data':
                mode_label = "ទិន្នន័យ Test ដែលបង្កើតដោយប្រព័ន្ធ (Purge System Test Data)"
            elif mode == 'operational':
                mode_label = "ទិន្នន័យប្រតិបត្តិការសាកល្បង (Go-Live Operational Clean)"
            elif mode == 'factory':
                mode_label = "កំណត់ឡើងវិញទាំងអស់ (Complete Factory Reset)"
            else:
                mode_label = "ទិន្នន័យតាមជម្រើស (Custom Clean)"
            snapshot_name = res.get('safety_snapshot', '')

            if mode == 'test_data':
                summary_msg = (
                    f"🎉 <strong>បានលុប{mode_label}ដោយជោគជ័យ!</strong><br>"
                    f"• 👤 គណនី Test Users បានលុប: {counts['test_users']} គណនី<br>"
                    f"• 🏢 ការិយាល័យ Test បានលុប: {counts.get('departments', 0)} ការិយាល័យ<br>"
                    f"• 🚗 យានយន្ត & សំណើតេស្ត: {counts.get('vehicles', 0)} គ្រឿង, {counts.get('vehicle_requests', 0)} សំណើ<br>"
                    f"• 📁 ឯកសារតេស្តបានលុប: {counts.get('documents', 0)} ច្បាប់<br>"
                    f"• 💬 សារ & Notif តេស្ត: {counts.get('notifications', 0) + counts.get('chat_messages', 0)} items<br>"
                    f"• 🛡️ <strong>រក្សាទុក៖</strong> បញ្ជីមន្ត្រីរាជការ, មន្ត្រីកិច្ចសន្យា និងគណនីផ្លូវការដដែល ១០០%!<br>"
                )
            else:
                summary_msg = (
                    f"🎉 <strong>បានសម្អាត{mode_label}ដោយជោគជ័យ!</strong><br>"
                    f"• 📁 ឯកសារ & Version: {counts['documents']} ច្បាប់ ({counts['document_versions']} ឯកសារ, {counts['annotations']} ចំណារ)<br>"
                    f"• 📋 កំណត់ត្រាវត្តមាន: {counts['attendance']} records<br>"
                    f"• 🚗 សំណើយានយន្ត: {counts['vehicle_requests']} requests<br>"
                    f"• 🎖️ សំណើ HR & Audit Log: {counts['promotion_requests'] + counts['medal_requests']} requests, {counts['audit_logs']} logs<br>"
                    f"• 💬 សារ & Notif: {counts['notifications'] + counts['chat_messages']} items<br>"
                )
                if counts.get('civil_servants', 0) > 0 or counts.get('contract_officers', 0) > 0:
                    summary_msg += f"• 👥 មន្ត្រីរាជការ & កិច្ចសន្យា: {counts['civil_servants']} នាក់ (+{counts['contract_officers']} កិច្ចសន្យា)<br>"
                if counts.get('test_users', 0) > 0:
                    summary_msg += f"• 👤 គណនីអ្នកប្រើប្រាស់សាកល្បង: {counts['test_users']} accounts<br>"
                if counts.get('departments', 0) > 0:
                    summary_msg += f"• 🏢 ការិយាល័យ: {counts['departments']} ការិយាល័យ<br>"

            if counts.get('media_files', 0) > 0:
                summary_msg += f"• 🖼️ ឯកសារ Media Uploads សម្អាតបាន: {counts['media_files']} files<br>"

            summary_msg += f"<small class='text-muted'>🛡️ ប្រព័ន្ធបានបង្កើត Safety Snapshot រួចរាល់មុនពេលលុប៖ <strong>{snapshot_name}</strong> (លោកអ្នកអាច Restore មកវិញបានគ្រប់ពេល)</small>"

            messages.success(request, summary_msg)
        else:
            messages.error(request, f"❌ បរាជ័យក្នុងការសម្អាតទិន្នន័យ: {res.get('error')}")
    except Exception as e:
        messages.error(request, f"❌ កំហុសបច្ចេកទេសក្នុងពេលសម្អាត: {str(e)}")

    return redirect('backup_sync_dashboard')


@admin_only_required
def api_clean_preview(request):
    """
    AJAX endpoint returning current counts of data for live preview.
    """
    if not (request.user.is_superuser or request.user.username.upper() == 'ADMIN'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    counts = get_clean_preview_counts()
    return JsonResponse({'success': True, 'counts': counts})


@admin_only_required
def api_generate_backup(request):
    """
    AJAX endpoint to generate backup packages (FULL, DATABASE_ONLY, MEDIA_ONLY, SNAPSHOT)
    with progress tracking support and direct file saving.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

    backup_type = request.POST.get('backup_type', 'FULL').upper()
    custom_filename = request.POST.get('custom_filename', '').strip()
    note = request.POST.get('note', '').strip()
    user_note = note or f"Generated via Web UI by {request.user.get_full_name() or request.user.username}"

    try:
        if backup_type == 'DATABASE_ONLY':
            res = create_db_backup(user=request.user, note=user_note)
        elif backup_type == 'MEDIA_ONLY':
            res = create_media_backup(user=request.user, note=user_note)
        elif backup_type == 'SNAPSHOT':
            res = create_full_backup(user=request.user, note=user_note or "Local Server Snapshot created via Web UI")
        else:  # FULL
            res = create_full_backup(user=request.user, note=user_note)

        if not res.get('success'):
            return JsonResponse({'success': False, 'error': res.get('error', 'Failed to generate backup')}, status=500)

        filename = res['filename']

        # If user specified a custom filename, rename the created zip
        if custom_filename and custom_filename != filename:
            safe_name = os.path.basename(custom_filename)
            if not safe_name.lower().endswith('.zip'):
                safe_name += '.zip'
            old_file = Path(res['file_path'])
            new_file = BACKUP_DIR / safe_name
            if old_file.exists():
                try:
                    if new_file.exists():
                        os.remove(new_file)
                    os.rename(old_file, new_file)
                    filename = safe_name
                    res['filename'] = filename
                    res['file_path'] = str(new_file)
                except Exception:
                    pass

        download_url = reverse('download_local_backup_file', kwargs={'filename': filename})

        type_labels = {
            'FULL': 'Full System Backup (.zip)',
            'DATABASE_ONLY': 'Database Only Backup (.zip)',
            'MEDIA_ONLY': 'Media Attachments Only (.zip)',
            'SNAPSHOT': 'Local Server Snapshot (.zip)',
        }

        return JsonResponse({
            'success': True,
            'filename': filename,
            'file_size_mb': res.get('file_size_mb', 0),
            'download_url': download_url,
            'backup_type': backup_type,
            'type_label': type_labels.get(backup_type, backup_type),
            'created_at': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
            'local_path': str(BACKUP_DIR / filename),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)




# ==============================================================================
# AJAX CLIENT SYNC API (Triggers client-to-server operations from Dashboard UI)
# ==============================================================================

@admin_only_required
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


@admin_only_required
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
