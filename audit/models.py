import datetime
import decimal
from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet

from common.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    """
    Generic audit log entry.

    - user: who performed the action (can be null for system tasks)
    - action: what happened (create/update/delete/etc.)
    - app_label + model_name: where it happened
    - object_id: primary key of the affected object as string
    - changes: structured diff or payload describing the change
    - extra: optional extra metadata (e.g. IP, user agent, etc.)
    """

    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),

        ('user_created', 'User Created'),
        ('user_updated', 'User Updated'),
        ('user_activated', 'User Activated'),
        ('user_deactivated', 'User Deactivated'),
        ('role_permissions_updated', 'Role Permissions Updated'),
        ('user_page_permissions_updated', 'User Page Permissions Updated'),

        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100, choices=ACTION_CHOICES)

    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)

    changes = models.JSONField(null=True, blank=True)
    extra = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['app_label', 'model_name']),
            models.Index(fields=['object_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f'[{self.action}] {self.app_label}.{self.model_name} ({self.object_id})'


def _make_json_serializable(value):
    """
    Recursively convert values into JSON-serializable forms.
    """
    # QuerySet (e.g., ManyToMany cleaned_data can return this)
    if isinstance(value, QuerySet):
        return [_make_json_serializable(v) for v in value]

    # Many-to-many manager (e.g., instance.roles)
    if isinstance(value, models.Manager):
        # If it's a related manager, .all() returns a QuerySet
        try:
            return [_make_json_serializable(v) for v in value.all()]
        except Exception:
            # Fallback for non-related managers
            return str(value)

    # Django model instances (FK, etc.)
    if isinstance(value, models.Model):
        return {
            # 'pk': str(value.pk), # Enable if required to view PK
            'label': str(value),
            'model': value._meta.label,
        }

    # Dates / datetimes / times
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()

    # Decimal (money)
    if isinstance(value, decimal.Decimal):
        return str(value)  # safe, preserves precision

    if isinstance(value, bool):
        return str(value)

    # Collections
    if isinstance(value, (list, tuple)):
        return [_make_json_serializable(v) for v in value]

    if isinstance(value, dict):
        return {k: _make_json_serializable(v) for k, v in value.items()}

    # Primitives (str, int, float, bool, None) pass through
    return value


def _normalize_changes_for_action(action: str, changes: dict | None) -> dict:
    """
    Normalize the `changes` structure so that in the DB we always have:

        {
            'field_name': {
                'old': <old value or None>,
                'new': <new value or None>,
            },
            ...
        }

    - For 'create':
        input:  {'name': 'India', 'iso_code': 'IN'}
        stored: {'name': {'old': None, 'new': 'India'}, ...}

    - For 'update':
        if view already passes:
            {'name': {'old': 'Old', 'new': 'New'}}
        we just serialize inner values.

        if view passes raw:
            {'name': 'India'}
        we treat as {'old': None, 'new': 'India'} as fallback.
    """
    changes = changes or {}
    normalized = {}

    action = (action or '').lower()

    if action == 'create' or 'created' in action:
        # Everything is 'new' – no old values
        for field, value in changes.items():
            normalized[field] = {
                'old': None,
                'new': value,
            }

    elif action == 'update' or 'updated' in action:
        for field, value in changes.items():
            # If already in {'old': ..., 'new': ...} shape, keep it
            if isinstance(value, dict) and 'old' in value and 'new' in value:
                normalized[field] = {
                    'old': value.get('old'),
                    'new': value.get('new'),
                }
            else:
                # Fallback: treat as 'new' only
                normalized[field] = {
                    'old': None,
                    'new': value,
                }
    elif action == 'delete' or 'deleted' in action:
        # Snapshot before delete: old=value, new=None
        for field, value in changes.items():
            normalized[field] = {'old': value, 'new': None}
    else:
        # For other actions, just dump as given
        normalized = changes

    # Finally, make everything JSON-serializable
    return _make_json_serializable(normalized)


def log_action(user, action: str, instance=None, changes=None, extra=None):
    """
    Helper to quickly create an AuditLog row.

    Example (create):
        log_action(request.user, 'create', obj, changes=form.cleaned_data)

    Example (update):
        log_action(request.user, 'update', obj, changes={
            'name': {'old': 'Old', 'new': 'New'}
        })
    """

    app_label = ''
    model_name = ''
    object_id = ''

    if instance is not None:
        ct = ContentType.objects.get_for_model(
            instance.__class__,
            for_concrete_model=False,
        )
        app_label = ct.app_label
        model_name = ct.model
        object_id = str(instance.pk)

    normalized_changes = _normalize_changes_for_action(action, changes)
    serializable_extra = _make_json_serializable(extra or {})

    AuditLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        action=action,
        app_label=app_label,
        model_name=model_name,
        object_id=object_id,
        changes=normalized_changes,
        extra=serializable_extra,
    )

"""
from audit.models import log_action

def form_valid(self, form):
    response = super().form_valid(form)
    log_action(self.request.user, 'update', self.object, changes=form.changed_data)
    return response
"""
