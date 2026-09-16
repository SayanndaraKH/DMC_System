import os
import json
import logging
from pathlib import Path
from datetime import datetime
import requests

from django.conf import settings
from .backup_service import create_full_backup, restore_backup, get_system_stats, BACKUP_DIR, TEMP_DIR

logger = logging.getLogger(__name__)

# Default Sync Token if not explicitly set in environment
DEFAULT_SYNC_TOKEN = getattr(
    settings,
    'SYNC_AUTH_TOKEN',
    os.environ.get('SYNC_AUTH_TOKEN', 'dms-secure-sync-token-2026-cambodia-gov')
)

def get_default_sync_token():
    return getattr(
        settings,
        'SYNC_AUTH_TOKEN',
        os.environ.get('SYNC_AUTH_TOKEN', DEFAULT_SYNC_TOKEN)
    )

def ping_server(server_url, token=None):
    """
    Pings the central/remote DMS server to check connectivity and online status.
    """
    token = token or get_default_sync_token()
    clean_url = server_url.rstrip('/')
    target_endpoint = f"{clean_url}/api/sync/ping/"
    
    headers = {
        'Authorization': f"Bearer {token}",
        'User-Agent': 'DMS-SyncClient/1.0',
    }

    try:
        resp = requests.get(target_endpoint, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'online': True,
                'status_code': 200,
                'server_time': data.get('server_time'),
                'server_name': data.get('system_name', 'DMS Server'),
                'stats': data.get('stats', {}),
                'message': 'Connected successfully',
            }
        elif resp.status_code in [401, 403]:
            return {
                'online': False,
                'status_code': resp.status_code,
                'error': 'លេខកូដសម្ងាត់សមកាលកម្ម (Sync Token) មិនត្រឹមត្រូវ។ (Invalid Sync Token)',
            }
        else:
            return {
                'online': False,
                'status_code': resp.status_code,
                'error': f"ម៉ាស៊ីនមេឆ្លើយតបកូដកំហុស: HTTP {resp.status_code}",
            }
    except requests.exceptions.ConnectionError:
        return {
            'online': False,
            'error': 'មិនអាចភ្ជាប់ទៅកាន់ម៉ាស៊ីនមេបានឡើយ (Connection Refused/Offline)។ សូមពិនិត្យមើល URL និងការតភ្ជាប់ Internet/LAN។',
        }
    except requests.exceptions.Timeout:
        return {
            'online': False,
            'error': 'ការតភ្ជាប់លើសកំណត់ពេលវេលា (Connection Timeout)។ ម៉ាស៊ីនមេយឺត ឬមិនដំណើរការ។',
        }
    except Exception as e:
        return {
            'online': False,
            'error': f"កំហុសក្នុងការតភ្ជាប់: {str(e)}",
        }


def push_to_server(server_url, token=None, user=None):
    """
    Pushes local data and media attachments to the central/remote DMS server.
    Creates a full backup bundle locally, then uploads it to server's /api/sync/receive/ endpoint.
    """
    token = token or get_default_sync_token()
    clean_url = server_url.rstrip('/')
    target_endpoint = f"{clean_url}/api/sync/receive/"

    # Step 1: Create local sync package
    backup_res = create_full_backup(user=user, note='Auto-generated bundle for Push Sync')
    if not backup_res.get('success'):
        return {
            'success': False,
            'error': f"Failed to create local sync package: {backup_res.get('error')}",
        }

    file_path = backup_res['file_path']

    headers = {
        'Authorization': f"Bearer {token}",
        'User-Agent': 'DMS-SyncClient/1.0',
    }

    try:
        with open(file_path, 'rb') as f:
            files = {'sync_file': (backup_res['filename'], f, 'application/zip')}
            data = {
                'source_machine': getattr(user, 'username', 'LocalPC'),
                'sync_timestamp': datetime.now().isoformat(),
            }
            resp = requests.post(target_endpoint, headers=headers, files=files, data=data, timeout=300)

        if resp.status_code == 200:
            result = resp.json()
            return {
                'success': True,
                'message': 'បានបញ្ជូន និងសមកាលកម្មទិន្នន័យទៅកាន់ម៉ាស៊ីនមេដោយជោគជ័យ!',
                'server_report': result,
                'package_size_mb': backup_res.get('file_size_mb'),
            }
        else:
            try:
                err_data = resp.json()
                err_msg = err_data.get('error', resp.text)
            except Exception:
                err_msg = resp.text
            return {
                'success': False,
                'error': f"Server returned error (HTTP {resp.status_code}): {err_msg}",
            }
    except requests.exceptions.RequestException as req_err:
        return {
            'success': False,
            'error': f"Network transfer failed: {str(req_err)}",
        }


def pull_from_server(server_url, token=None, user=None):
    """
    Pulls data and media files from the central/remote DMS server into local PC.
    Downloads the server's export package and performs a Smart Lossless Merge.
    """
    token = token or get_default_sync_token()
    clean_url = server_url.rstrip('/')
    target_endpoint = f"{clean_url}/api/sync/export/"

    headers = {
        'Authorization': f"Bearer {token}",
        'User-Agent': 'DMS-SyncClient/1.0',
    }

    temp_save_path = TEMP_DIR / f"pulled_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    try:
        with requests.get(target_endpoint, headers=headers, stream=True, timeout=300) as resp:
            if resp.status_code != 200:
                try:
                    err_msg = resp.json().get('error', resp.text)
                except Exception:
                    err_msg = resp.text
                return {
                    'success': False,
                    'error': f"Failed to download data from server (HTTP {resp.status_code}): {err_msg}",
                }

            with open(temp_save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)

        # Step 2: Perform smart merge restore
        restore_result = restore_backup(temp_save_path, mode='merge')
        
        # Clean up temp pull file
        if temp_save_path.exists():
            try:
                os.remove(temp_save_path)
            except OSError:
                pass

        if restore_result.get('success'):
            return {
                'success': True,
                'message': 'បានទាញ និងសមកាលកម្មទិន្នន័យពីម៉ាស៊ីនមេចូលកុំព្យូទ័រដោយជោគជ័យ!',
                'restore_report': restore_result,
            }
        else:
            return {
                'success': False,
                'error': f"Restore failed on local machine: {restore_result.get('error')}",
                'restore_report': restore_result,
            }

    except requests.exceptions.RequestException as req_err:
        if temp_save_path.exists():
            try:
                os.remove(temp_save_path)
            except OSError:
                pass
        return {
            'success': False,
            'error': f"Network error during download: {str(req_err)}",
        }


def bidirectional_sync(server_url, token=None, user=None):
    """
    Performs a 2-way synchronization:
    Step 1: Pull newest changes from central server to local machine.
    Step 2: Push local changes back to the central server.
    """
    # 1. Pull first
    pull_res = pull_from_server(server_url, token=token, user=user)
    if not pull_res.get('success'):
        return {
            'success': False,
            'step': 'PULL',
            'error': f"ដំណាក់កាលទាញទិន្នន័យពីម៉ាស៊ីនមេ (Pull) បរាជ័យ: {pull_res.get('error')}",
            'pull_report': pull_res,
        }

    # 2. Push second
    push_res = push_to_server(server_url, token=token, user=user)
    if not push_res.get('success'):
        return {
            'success': False,
            'step': 'PUSH',
            'error': f"ដំណាក់កាលបញ្ជូនទិន្នន័យទៅម៉ាស៊ីនមេ (Push) បរាជ័យ: {push_res.get('error')}",
            'pull_report': pull_res,
            'push_report': push_res,
        }

    return {
        'success': True,
        'message': 'សមកាលកម្មទិន្នន័យទាំងសងខាង (2-Way Sync) បានសម្រេចដោយជោគជ័យ!',
        'pull_report': pull_res,
        'push_report': push_res,
    }
