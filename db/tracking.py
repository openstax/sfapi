from django.db import models


class ChangeTrackingMixin(models.Model):
    """Mixin that tracks field-level changes on save() and creates FieldChangeLog entries."""

    # Fields to track — override in subclass if needed
    _tracked_fields = None
    # Default change source — can be overridden per-save via _change_source attribute
    _change_source = 'api'
    _changed_by = ''

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        change_source = getattr(self, '_change_source', 'api')
        changed_by = getattr(self, '_changed_by', '')

        if self.pk:
            try:
                old_instance = type(self).objects.get(pk=self.pk)
                changes = self._get_changes(old_instance)
                if changes:
                    self._log_changes(changes, change_source, changed_by)
            except type(self).DoesNotExist:
                pass  # New record, no changes to track

        super().save(*args, **kwargs)

    def _get_tracked_fields(self):
        if self._tracked_fields is not None:
            return self._tracked_fields
        # Default: track all concrete fields except auto-managed ones
        skip = {'local_create_date', 'local_update_date', 'id'}
        return [f.name for f in self._meta.concrete_fields if f.name not in skip]

    def _get_changes(self, old_instance):
        changes = []
        for field_name in self._get_tracked_fields():
            old_val = getattr(old_instance, field_name)
            new_val = getattr(self, field_name)
            if old_val != new_val:
                changes.append((field_name, str(old_val) if old_val is not None else None,
                                str(new_val) if new_val is not None else None))
        return changes

    def _log_changes(self, changes, change_source, changed_by):
        from api.models import FieldChangeLog
        logs = [
            FieldChangeLog(
                model_name=type(self).__name__,
                record_id=str(self.pk),
                field_name=field_name,
                old_value=old_val,
                new_value=new_val,
                change_source=change_source,
                changed_by=changed_by,
            )
            for field_name, old_val, new_val in changes
        ]
        FieldChangeLog.objects.bulk_create(logs)
