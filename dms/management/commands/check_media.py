import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Reports where MEDIA_ROOT points and whether it looks like a persistent '
        'storage volume. Run at boot so uploaded photos vanishing after a deploy '
        'is visible in the logs instead of being a mystery.'
    )

    def handle(self, *args, **options):
        media_root = os.path.abspath(str(settings.MEDIA_ROOT))
        volume_mount = os.environ.get('VOLUME_MOUNT_PATH') or os.environ.get('DATA_DIR')
        self.stdout.write(f'[check_media] MEDIA_ROOT = {media_root}')
        self.stdout.write(f'[check_media] MEDIA_ROOT env override = {os.environ.get("MEDIA_ROOT") or "(not set)"}')
        self.stdout.write(f'[check_media] VOLUME_MOUNT_PATH = {volume_mount or "(not set - no volume attached)"}')

        file_count = 0
        total_bytes = 0
        for root, _dirs, files in os.walk(media_root):
            for name in files:
                file_count += 1
                try:
                    total_bytes += os.path.getsize(os.path.join(root, name))
                except OSError:
                    pass
        self.stdout.write(
            f'[check_media] {file_count} file(s), {total_bytes / 1048576:.1f} MB currently stored'
        )

        # MEDIA_ROOT is safe if it sits on a volume: either it is itself a mount
        # point, or it lives underneath the path the volume was mounted at.
        on_volume = os.path.ismount(media_root)
        if not on_volume and volume_mount:
            mount_abs = os.path.abspath(volume_mount)
            on_volume = media_root == mount_abs or media_root.startswith(mount_abs + os.sep)

        if on_volume:
            usage = shutil.disk_usage(media_root)
            self.stdout.write(self.style.SUCCESS(
                f'[check_media] OK - {media_root} is a separate mount point '
                f'({usage.free / 1073741824:.1f} GB free). Uploads will survive deploys.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'[check_media] WARNING - {media_root} is NOT a mounted volume. '
                'It lives on the ephemeral filesystem and uploaded files may be '
                'lost on the next deploy. Attach a persistent volume to this service '
                f'with mount path {media_root}'
            ))
