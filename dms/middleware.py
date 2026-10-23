import os
import time
import logging
from django.db import connection
from django.db.utils import OperationalError, InterfaceError
from django.http import HttpResponse

logger = logging.getLogger('dms.neon_retry')

# Markers identifying retryable database connection drops, Neon sleeping/waking cold starts, or network interruptions
RETRYABLE_ERROR_MARKERS = [
    'server closed the connection unexpectedly',
    'terminating connection due to administrator command',
    'could not connect to server',
    'connection refused',
    'connection reset by peer',
    'timeout expired',
    'the connection is closed',
    'ssl syscall error',
    'broken pipe',
    'connection to server',
    'canceling statement due to statement timeout',
    'operationalerror',
]


def is_retryable_db_error(exc):
    if not isinstance(exc, (OperationalError, InterfaceError)):
        return False
    msg = str(exc).lower()
    return any(marker in msg for marker in RETRYABLE_ERROR_MARKERS)


def render_khmer_db_offline_page(error_detail=""):
    """
    Renders an elegant, official Khmer retry screen when Cloud Database connection is temporarily unreachable.
    """
    html = f"""<!DOCTYPE html>
<html lang="km">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>កំពុងតភ្ជាប់ទៅកាន់ Cloud Database... | DMC System</title>
    <link href="https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body {{
            font-family: 'Kantumruy Pro', sans-serif;
            background: #0f172a;
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }}
        .card {{
            background: #1e293b;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 35px 30px;
            max-width: 540px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }}
        .icon-wrap {{
            width: 75px;
            height: 75px;
            background: rgba(245, 158, 11, 0.15);
            border: 2px solid rgba(245, 158, 11, 0.4);
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }}
        h2 {{
            margin: 0 0 10px;
            font-size: 1.35rem;
            color: #f8fafc;
            font-weight: 700;
        }}
        p {{
            color: #94a3b8;
            font-size: 0.95rem;
            line-height: 1.6;
            margin: 0 0 25px;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            color: #ffffff;
            font-family: inherit;
            font-size: 0.95rem;
            font-weight: 600;
            padding: 12px 28px;
            border-radius: 9999px;
            border: none;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35);
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45);
        }}
        .btn-outline {{
            background: transparent;
            border: 1px solid rgba(255,255,255,0.2);
            color: #cbd5e1;
            box-shadow: none;
            margin-left: 8px;
        }}
        .btn-outline:hover {{
            background: rgba(255,255,255,0.08);
            color: #fff;
        }}
        .small-hint {{
            margin-top: 25px;
            font-size: 0.8rem;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-wrap">
            <i class="fa-solid fa-cloud-arrow-down fa-2x" style="color: #f59e0b;"></i>
        </div>
        <h2>កំពុងភ្ជាប់ទៅកាន់ Neon Cloud Database</h2>
        <p>
            ម៉ាស៊ីនបម្រើ Cloud Database កំពុងបើកដំណើរការឡើងវិញ (Wake-up / Cold Start) ឬបណ្តាញអ៊ីនធឺណិតមានការរអាក់រអួលមួយភ្លែត។
            សូមរង់ចាំប្រមាណ ២ ទៅ ៣ វិនាទី រួចចុចប៊ូតុងខាងក្រោមដើម្បីព្យាយាមម្តងទៀត។
        </p>
        <div>
            <button class="btn" onclick="window.location.reload();">
                <i class="fa-solid fa-rotate-right"></i> ព្យាយាមភ្ជាប់ម្តងទៀត (Retry)
            </button>
            <a href="/" class="btn btn-outline">
                <i class="fa-solid fa-house"></i> ទៅផ្ទាំងដើម
            </a>
        </div>
        <div class="small-hint">
            <i class="fa-solid fa-shield-halved me-1"></i> ប្រព័ន្ធគ្រប់គ្រងធនធានមនុស្ស និងឯកសារ (DMC System)
        </div>
    </div>
    <script>
        // Auto retry once after 3 seconds
        setTimeout(function() {{
            if (!sessionStorage.getItem('neon_auto_retried')) {{
                sessionStorage.setItem('neon_auto_retried', '1');
                window.location.reload();
            }} else {{
                sessionStorage.removeItem('neon_auto_retried');
            }}
        }}, 3000);
    </script>
</body>
</html>"""
    return HttpResponse(html, status=503)


class NeonDatabaseRetryMiddleware:
    """
    Middleware that automatically catches Neon Cloud serverless auto-suspend / cold-boot OperationalErrors
    and momentary network drops.
    It closes the dead socket, waits briefly for Neon compute resumption, and retries the request seamlessly.
    """
    MAX_RETRIES = 3
    DELAYS = [1.0, 1.8, 2.5]  # seconds to wait for Neon cold-boot wake up

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        last_exception = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.get_response(request)
                return response
            except Exception as e:
                if not is_retryable_db_error(e):
                    raise

                last_exception = e
                logger.warning(
                    f"Neon Cloud DB connection drop detected on attempt {attempt + 1}/{self.MAX_RETRIES}: {e}"
                )

                # 1. Close dead connection socket
                try:
                    connection.close()
                except Exception:
                    pass

                # 2. Wait for Neon compute instance to wake up
                if attempt < self.MAX_RETRIES - 1:
                    sleep_sec = self.DELAYS[attempt]
                    time.sleep(sleep_sec)

                    # 3. Test reconnect before retrying the view
                    try:
                        connection.ensure_connection()
                    except Exception as reconn_err:
                        logger.debug(f"Neon reconnection warmup: {reconn_err}")

        # If all retries exhausted, present clean Khmer retry page instead of yellow traceback
        logger.error(f"Neon Cloud DB retry exhausted after {self.MAX_RETRIES} attempts: {last_exception}")
        return render_khmer_db_offline_page(str(last_exception))
