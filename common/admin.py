from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Page, RolePagePermission, UserPagePermission


# -------------------------
#  User Page Permission Inline
# -------------------------
class UserPagePermissionInline(admin.TabularInline):
    model = UserPagePermission
    extra = 0
    autocomplete_fields = ['page', 'created_by']
    readonly_fields = ['created_at', 'updated_at']


# -------------------------
#  User Admin
# -------------------------
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_first_login', 'is_active', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)

    fieldsets = (
        ('Login Credentials', {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Role & Access', {'fields': ('role', 'is_first_login', 'created_by')}),
        ('Permissions Flags', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ('created_at', 'updated_at')

    inlines = [UserPagePermissionInline]


# -------------------------
#  Page Admin
# -------------------------
@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at', 'updated_at')
    search_fields = ('name', 'code')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')


# -------------------------
#  Role Page Permission Admin
# -------------------------
@admin.register(RolePagePermission)
class RolePagePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'page', 'access_type', 'created_at')
    list_filter = ('role', 'access_type')
    search_fields = ('role', 'page__name', 'page__code')
    autocomplete_fields = ['page']
    readonly_fields = ('created_at', 'updated_at')


# -------------------------
#  User Page Permission Admin
# -------------------------
@admin.register(UserPagePermission)
class UserPagePermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'page', 'access_type', 'created_by', 'created_at')
    list_filter = ('access_type',)
    search_fields = ('user__username', 'page__name', 'page__code')
    autocomplete_fields = ['user', 'page', 'created_by']
    readonly_fields = ('created_at', 'updated_at')
