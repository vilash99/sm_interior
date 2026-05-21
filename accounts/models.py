from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    ROLE_CHOICES = [
        ('superuser', 'SuperUser'),
        ('admin', 'Admin'),
        ('standard', 'Standard'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='standard')
    is_first_login = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
    )

    ACCESS_HIERARCHY = {
        'view': 1,
        'edit': 2,
        'full': 3,
    }

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'superuser'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    def has_page_access(self, page_code: str, access_type: str = 'view') -> bool:
        """
        Core API: call this everywhere (views, templates, menus).
        1. Superuser shortcut
        2. Check user-specific override
        3. Fall back to role-based permission
        """
        # 1) Superuser always allowed
        if self.is_superuser or self.role == 'superuser':
            return True

        # 2) Per-user override
        override = UserPagePermission.get_effective_access(self, page_code)
        if override is not None:
            if override == 'denied':
                return False
            return self._meets_access_level(override, access_type)

        # 3) Role-based default
        role_access = RolePagePermission.get_effective_access(self.role, page_code)
        if role_access is None or role_access == 'denied':
            return False

        return self._meets_access_level(role_access, access_type)

    def _meets_access_level(self, granted: str, required: str) -> bool:
        granted_level = self.ACCESS_HIERARCHY.get(granted, 0)
        required_level = self.ACCESS_HIERARCHY.get(required, 1)
        return granted_level >= required_level

    def permission_summary(self):
        """
        Optional helper: return dict of all pages + view/edit/full booleans.
        Great for showing in admin or a “Permissions” page.
        """
        data = {}
        for page in Page.objects.all():
            data[page.code] = {
                'view': self.has_page_access(page.code, 'view'),
                'edit': self.has_page_access(page.code, 'edit'),
                'full': self.has_page_access(page.code, 'full'),
            }
        return data


class Page(TimeStampedModel):
    """
    Logical page/feature of the system.
    code: internal identifier used in permission checks.
    name: human-friendly label.
    """
    code = models.SlugField(max_length=50, unique=True)  # e.g. 'doctors', 'letters'
    name = models.CharField(max_length=100)              # e.g. 'Doctors'
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Page'
        verbose_name_plural = 'Pages'

    def __str__(self):
        return f'{self.name} ({self.code})'


class RolePagePermission(TimeStampedModel):
    ACCESS_TYPES = [
        ('view', 'View Only'),
        ('edit', 'Edit'),
        ('full', 'Full'),
        ('denied', 'Access Denied'),
    ]

    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='role_permissions')
    access_type = models.CharField(max_length=10, choices=ACCESS_TYPES)

    class Meta:
        unique_together = ('role', 'page')
        verbose_name = 'Role Page Permission'
        verbose_name_plural = 'Role Page Permissions'

    def __str__(self):
        return f'{self.role} → {self.page.code} ({self.get_access_type_display()})'

    @classmethod
    def get_effective_access(cls, role: str, page_code: str) -> str | None:
        try:
            perm = cls.objects.select_related('page').get(
                role=role,
                page__code=page_code,
            )
            return perm.access_type
        except cls.DoesNotExist:
            return None


class UserPagePermission(TimeStampedModel):
    ACCESS_TYPES = [
        ('view', 'View Only'),
        ('edit', 'Edit'),
        ('full', 'Full'),
        ('denied', 'Access Denied'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='page_permissions')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='user_permissions')
    access_type = models.CharField(max_length=10, choices=ACCESS_TYPES)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_page_permissions',
    )

    class Meta:
        unique_together = ('user', 'page')
        verbose_name = 'User Page Permission'
        verbose_name_plural = 'User Page Permissions'

    def __str__(self):
        return f'{self.user.username} → {self.page.code} ({self.get_access_type_display()})'

    @classmethod
    def get_effective_access(cls, user: User, page_code: str) -> str | None:
        try:
            perm = cls.objects.select_related('page').get(
                user=user,
                page__code=page_code,
            )
            return perm.access_type
        except cls.DoesNotExist:
            return None
