"""
DOCX to PDF Conversion and Word Automation Service for DMC System.
Uses Microsoft Word COM (win32com) or PowerShell fallback to render
DOCX files with 100% identical formatting, Khmer fonts, and layout.
"""

import os
import sys
import subprocess
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def convert_docx_to_pdf_word_com(docx_path, pdf_path):
    """
    Converts a DOCX file to PDF using Microsoft Word COM Automation.
    Guarantees 100% layout, font, and table preservation identical to MS Word.
    """
    docx_path = os.path.abspath(str(docx_path))
    pdf_path = os.path.abspath(str(pdf_path))

    if not os.path.exists(docx_path):
        logger.error(f"DOCX source file not found: {docx_path}")
        return False

    # Ensure parent dir exists
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Method 1: Try Python win32com
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        word = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0  # wdAlertsNone = 0
            doc = word.Documents.Open(docx_path, ReadOnly=True, ConfirmConversions=False)
            doc.SaveAs(pdf_path, FileFormat=17)  # wdFormatPDF = 17
            doc.Close(SaveChanges=False)
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                logger.info(f"Successfully converted DOCX to PDF via win32com: {pdf_path}")
                return True
        finally:
            if word:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    except Exception as e:
        logger.warning(f"win32com conversion failed: {e}. Attempting PowerShell fallback...")

    # Method 2: PowerShell Word COM Fallback (Works on all Windows machines without pywin32)
    if sys.platform == "win32":
        try:
            ps_script = f"""
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {{
    $d = $w.Documents.Open('{docx_path}', $false, $true)
    $d.SaveAs([ref]'{pdf_path}', [ref]17)
    $d.Close([ref]$false)
}} finally {{
    $w.Quit()
}}
"""
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=45
            )
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                logger.info(f"Successfully converted DOCX to PDF via PowerShell: {pdf_path}")
                return True
            else:
                logger.error(f"PowerShell conversion failed: {res.stderr}")
        except Exception as pe:
            logger.error(f"PowerShell execution error: {pe}")

    return False


def get_cached_pdf_path(docx_path):
    """Returns standard cached PDF file path corresponding to a docx file."""
    p = Path(docx_path)
    return str(p.with_suffix(".docx.pdf"))


def get_or_convert_docx_to_pdf(docx_path, sync_to_cloud=True):
    """
    Returns the path to a high-fidelity PDF corresponding to docx_path.
    If cached PDF exists and is up to date, returns immediately.
    Otherwise converts via MS Word and caches the result.
    """
    if not docx_path or not os.path.exists(docx_path):
        return None

    pdf_path = get_cached_pdf_path(docx_path)

    # Check existing valid cache
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        if os.path.getmtime(pdf_path) >= os.path.getmtime(docx_path):
            return pdf_path

    # Convert via Word COM
    ok = convert_docx_to_pdf_word_com(docx_path, pdf_path)
    if ok and os.path.exists(pdf_path):
        if sync_to_cloud:
            # Sync converted PDF to Neon Cloud in background thread
            def _sync():
                try:
                    from dms.media_service import upload_file_to_neon_cloud
                    from django.conf import settings
                    rel = os.path.relpath(pdf_path, settings.MEDIA_ROOT).replace('\\', '/')
                    upload_file_to_neon_cloud(pdf_path, rel)
                except Exception as e:
                    logger.warning(f"Failed to sync converted PDF to Neon: {e}")

            threading.Thread(target=_sync, daemon=True).start()

        return pdf_path

    return None
