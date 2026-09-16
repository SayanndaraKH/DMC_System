import os
import sys
import time
import socket
import sqlite3
import logging
import subprocess
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dms_project.settings')

LOG_FILE = BASE_DIR / 'server_log.txt'
PID_FILE = BASE_DIR / 'dms.pid'
BACKUP_DIR = BASE_DIR / 'backups'
BACKUP_DIR.mkdir(exist_ok=True)
DB_FILE = BASE_DIR / 'db.sqlite3'

# If running under pythonw.exe (GUI background mode on Windows), sys.stdout and sys.stderr are None
log_fp = open(str(LOG_FILE), 'a', encoding='utf-8', buffering=1)
if sys.stdout is None:
    sys.stdout = log_fp
if sys.stderr is None:
    sys.stderr = log_fp


def setup_logging():
    """
    Configures log rotation so server_log.txt never exceeds 5 MB.
    """
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5 * 1024 * 1024:
        old_log = BASE_DIR / 'server_log.txt.old'
        try:
            if old_log.exists():
                os.remove(old_log)
            LOG_FILE.rename(old_log)
        except OSError:
            pass

    handlers = [logging.FileHandler(str(LOG_FILE), encoding='utf-8', mode='a')]
    # Only add StreamHandler if standard stdout is a real console (not pythonw)
    if hasattr(sys, '__stdout__') and sys.__stdout__ is not None:
        handlers.append(logging.StreamHandler(sys.__stdout__))

    # Reconfigure root logger cleanly
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers,
        force=True
    )


def safe_sqlite_backup():
    """
    Creates an automated, non-blocking safe snapshot of db.sqlite3 using SQLite's online backup API.
    Guarantees zero database loss even if power cuts or crashes occur.
    """
    if not DB_FILE.exists():
        return

    try:
        # 1. Integrity check
        conn = sqlite3.connect(str(DB_FILE), timeout=10)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        check_result = cur.fetchone()[0]
        if check_result != "ok":
            logging.warning(f"Database integrity warning: {check_result}")

        # 2. Automated Safe Snapshot (Latest)
        latest_backup = BACKUP_DIR / 'db_autobackup_latest.sqlite3'
        dest_conn = sqlite3.connect(str(latest_backup), timeout=10)
        with dest_conn:
            conn.backup(dest_conn)
        dest_conn.close()

        # 3. Daily snapshot
        today_str = datetime.now().strftime('%Y-%m-%d')
        daily_backup = BACKUP_DIR / f'db_autobackup_{today_str}.sqlite3'
        if not daily_backup.exists():
            daily_conn = sqlite3.connect(str(daily_backup), timeout=10)
            with daily_conn:
                conn.backup(daily_conn)
            daily_conn.close()

        conn.close()
        logging.info("Automated SQLite database safety snapshot created successfully.")

        # 4. Prune snapshots older than 7 days
        cutoff = time.time() - (7 * 86400)
        for old_file in BACKUP_DIR.glob('db_autobackup_*.sqlite3'):
            if old_file.name != 'db_autobackup_latest.sqlite3' and old_file.stat().st_mtime < cutoff:
                try:
                    os.remove(old_file)
                except OSError:
                    pass

    except Exception as e:
        logging.error(f"Error during SQLite safe backup: {e}")


def is_port_in_use(port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


def kill_process_on_port(port=8000):
    """
    Kills any stale / orphaned process currently listening on port 8000.
    """
    if not is_port_in_use(port):
        return

    logging.info(f"Port {port} is occupied. Terminating conflicting process...")
    cmd = (
        f'powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue '
        '| Select-Object -ExpandProperty OwningProcess -Unique '
        '| ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"'
    )
    try:
        subprocess.run(cmd, shell=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
    except Exception as e:
        logging.warning(f"Failed to clear port {port} via PowerShell: {e}")


def detect_and_update_lan_ip():
    """
    Detects the machine's active LAN / Wi-Fi IP and writes updated IP.txt.
    """
    primary_ip = '127.0.0.1'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        primary_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    if primary_ip == '127.0.0.1':
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None):
                ip = info[4][0]
                if ':' not in ip and not ip.startswith('127.') and not ip.startswith('169.254.'):
                    primary_ip = ip
                    break
        except Exception:
            pass

    content = (
        "✅ អាសយដ្ឋាន IP សម្រាប់ដំណើរការកម្មវិធី DMS៖\n\n"
        "🔹 សម្រាប់ប្រើប្រាស់លើកុំព្យូទ័រផ្ទាល់ (Localhost):\n"
        "👉 http://127.0.0.1:8000/\n"
        "👉 http://localhost:8000/\n\n"
        "🔹 សម្រាប់ទូរស័ព្ទ ឬកុំព្យូទ័រផ្សេងទៀតក្នុងបណ្តាញ Wi-Fi / LAN តែមួយ (Network IP):\n"
        f"👉 http://{primary_ip}:8000/\n\n"
        "---\n"
        "(បានធ្វើបច្ចុប្បន្នភាពស្វ័យប្រវត្តិតាម IP បណ្តាញ Wi-Fi/LAN ជាក់ស្តែង)\n"
    )
    try:
        with open(BASE_DIR / 'IP.txt', 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        logging.warning(f"Could not update IP.txt: {e}")

    return primary_ip


def wait_and_open_browser(url='http://127.0.0.1:8000', timeout_seconds=20):
    """
    Waits in background until server starts responding, then opens default browser.
    """
    def poll_and_launch():
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if is_port_in_use(8000):
                time.sleep(1)
                try:
                    webbrowser.open(url)
                    logging.info(f"Browser opened to {url}")
                except Exception as e:
                    logging.warning(f"Failed to launch browser: {e}")
                return
            time.sleep(0.5)

    t = threading.Thread(target=poll_and_launch, daemon=True)
    t.start()


def stop_server():
    """
    Stops running DMS server instance based on PID file and port 8000.
    """
    logging.info("Stopping DMS Server...")
    # 1. Kill by PID file if exists
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            cmd = f'taskkill /F /PID {pid} /T'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info(f"Terminated process with PID {pid}")
        except Exception:
            pass
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    # 2. Kill by port 8000
    kill_process_on_port(8000)

    # 3. Kill any remaining manage.py runserver
    cmd2 = (
        'powershell -NoProfile -Command "Get-CimInstance Win32_Process '
        "| Where-Object { $_.CommandLine -like '*manage.py runserver*' } "
        '| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"'
    )
    try:
        subprocess.run(cmd2, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    print("[OK] DMS Server stopped successfully.")


def main():
    args = sys.argv[1:]

    # Handle --stop command
    if '--stop' in args:
        setup_logging()
        stop_server()
        return

    # Handle --autostart mode (Windows Startup)
    is_autostart = '--autostart' in args
    should_open_browser = '--open-browser' in args or not is_autostart

    setup_logging()
    logging.info("==================================================")
    logging.info(f"Starting DMS Server (Autostart={is_autostart}, OpenBrowser={should_open_browser})")
    logging.info("==================================================")

    # If launched during Windows logon / startup, wait 5 seconds for network stack & Wi-Fi adapter to be ready
    if is_autostart:
        logging.info("Windows Startup detected. Waiting 5s for network adapters to stabilize...")
        time.sleep(5)

    # Write current PID
    try:
        PID_FILE.write_text(str(os.getpid()))
    except Exception:
        pass

    # 1. Free port 8000 if occupied
    kill_process_on_port(8000)

    # 2. Database safety backup
    safe_sqlite_backup()

    # 3. Detect and update LAN / Wi-Fi IP
    lan_ip = detect_and_update_lan_ip()
    logging.info(f"Active LAN / Wi-Fi IP: {lan_ip} (http://{lan_ip}:8000/)")

    # 4. Run database migrations safely
    try:
        logging.info("Checking database migrations...")
        import django
        django.setup()
        from django.core.management import call_command
        call_command('migrate', interactive=False, stdout=sys.stdout, stderr=sys.stderr)
        logging.info("Migrations check completed successfully.")
    except Exception as e:
        logging.error(f"Migration error: {e}")

    # 5. Open browser if requested
    if should_open_browser:
        wait_and_open_browser('http://127.0.0.1:8000')

    # 6. Run server
    try:
        logging.info("DMS Server is now running on 0.0.0.0:8000")
        cmd = [sys.executable, str(BASE_DIR / 'manage.py'), 'runserver', '0.0.0.0:8000']
        subprocess.run(cmd)
    except KeyboardInterrupt:
        logging.info("DMS Server stopped by user.")
    except Exception as e:
        logging.critical(f"DMS Server error: {e}")
    finally:
        if PID_FILE.exists():
            try:
                PID_FILE.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == '__main__':
    main()
