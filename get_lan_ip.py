"""Prints the active LAN IP and rewrites IP.txt (UTF-8). Used by RUN_DMS_CONSOLE.bat.

Kept as a file instead of `python -c` because cmd's `for /f` breaks on the commas,
parentheses and Khmer text an inline command would need.
"""
import sys

import run  # note: importing run redirects sys.stdout to server_log.txt

sys.__stdout__.write(run.detect_and_update_lan_ip() + "\n")
