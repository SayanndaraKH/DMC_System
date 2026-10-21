import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models

logger = logging.getLogger(__name__)

@receiver(post_save)
def auto_sync_files_to_cloud_storage(sender, instance, **kwargs):
    """
    Automatically uploads any newly saved FileField or ImageField
    in the 'dms' app to Neon Cloud Database (CloudMediaStorage).
    """
    if getattr(sender._meta, 'app_label', None) != 'dms':
        return

    # Skip CloudMediaStorage itself to prevent recursion
    if sender.__name__ == 'CloudMediaStorage':
        return

    for field in sender._meta.fields:
        if isinstance(field, (models.FileField, models.ImageField)):
            try:
                file_obj = getattr(instance, field.name, None)
                if file_obj and hasattr(file_obj, 'name') and file_obj.name:
                    from dms.media_service import sync_field_file_to_neon_async
                    sync_field_file_to_neon_async(file_obj)
            except Exception as e:
                logger.debug(f"Signal media upload notice: {e}")
