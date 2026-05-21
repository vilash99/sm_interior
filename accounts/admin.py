# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Page, RolePagePermission, UserPagePermission


class UserPagePermissionInline(admin.TabularInline):
    model = UserPagePermission
    fk_name = 'user'  # specify which FK to use for the inline
    extra = 0
    raw_id_fields = ('page', 'created_by')
    autocomplete_fields = ('page',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'is_superuser',
        'is_staff',
        'is_active',
        'is_first_login',
        'created_by',
        'date_joined',
    )
    list_filter = (
        'role',
        'is_superuser',
        'is_staff',
        'is_active',
        'is_first_login',
    )
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    inlines = [UserPagePermissionInline]

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        (
            'Permissions',
            {
                'fields': (
                    'role',
                    'is_first_login',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Relations', {'fields': ('created_by',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'username',
                    'email',
                    'first_name',
                    'last_name',
                    'role',
                    'password1',
                    'password2',
                    'is_staff',
                    'is_superuser',
                    'is_active',
                ),
            },
        ),
    )


class RolePagePermissionInline(admin.TabularInline):
    model = RolePagePermission
    extra = 0
    raw_id_fields = ('page',)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description')
    search_fields = ('name', 'code', 'description')
    ordering = ('code',)
    inlines = [RolePagePermissionInline]


@admin.register(RolePagePermission)
class RolePagePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'page', 'access_type')
    list_filter = ('role', 'access_type', 'page')
    search_fields = ('role', 'page__code', 'page__name')
    raw_id_fields = ('page',)


@admin.register(UserPagePermission)
class UserPagePermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'page', 'access_type', 'created_by')
    list_filter = ('access_type', 'page', 'user')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'page__code',
        'page__name',
    )
    raw_id_fields = ('user', 'page', 'created_by')
