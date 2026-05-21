from django.shortcuts import redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, UpdateView, CreateView

from audit.models import log_action
from common.mixins import FormInvalidMessageMixin

from .mixins import PageAccessRequiredMixin, PagePermissionContextMixin
from .models import Page, RolePagePermission, UserPagePermission
from .forms import UserForm

User = get_user_model()


# -------------------------
#  Auth Views
# -------------------------

class LoginView(FormInvalidMessageMixin, auth_views.LoginView):
    """
    Simple login view using Django's built-in auth.
    """
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True  # If already logged in, send them away

    def form_valid(self, form):
        """Log successful login and handle first login"""
        response = super().form_valid(form)

        user = self.request.user

        log_action(
            user=user,
            action='login',
            instance=user,
            changes=None,
            extra={'ip': self.request.META.get('REMOTE_ADDR')},
        )

        # Check if first login
        if user.is_first_login:
            messages.info(self.request, 'Welcome! Please change your password to continue.')
            return redirect('accounts:password_change')

        return response

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return settings.LOGIN_REDIRECT_URL


class LogoutView(LoginRequiredMixin, auth_views.LogoutView):
    """
    Logs the user out and redirects to login.
    """
    next_page = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        # We log before logout, while request.user is still set
        user = request.user if request.user.is_authenticated else None

        if user is not None:
            log_action(
                user=user,
                action='logout',
                instance=user,
                changes=None,
                extra={
                    'ip': request.META.get('REMOTE_ADDR'),
                },
            )
            messages.success(request, 'You have been logged out successfully.')

        # Let LogoutView handle the actual logout + redirect
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class PasswordChangeView(LoginRequiredMixin, FormInvalidMessageMixin, auth_views.PasswordChangeView):
    """
    Allow logged-in user to change their password.
    """
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('dashboard:index')

    def form_valid(self, form):
        """
        On successful password change:
        - Save new password
        - Log audit entry
        - Show success message
        """
        response = super().form_valid(form)

        user = self.request.user

        # If this was their first login, update the flag
        if user.is_first_login:
            user.is_first_login = False
            user.save()

        # Audit log: password changed
        log_action(
            user=user,
            action='password_change',
            instance=user,
            changes={'fields': ['password']},
            extra={'ip': self.request.META.get('REMOTE_ADDR')},
        )

        messages.success(self.request, 'Your password has been changed successfully.')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Shows basic information about the currently logged-in user.
    """
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        permissions = user.permission_summary()

        context['user_obj'] = user
        context['created_users'] = user.created_users.all()  # users this user has created
        context['permissions'] = permissions   # from your User model helper
        context['permission_items'] = permissions.items()

        return context


# -------------------------
#  Admin-style Views
# -------------------------

class UserToggleStatusView(PageAccessRequiredMixin, View):
    """
    Toggle active/inactive status for a user.
    Requires 'accounts_users' with 'edit' permission.
    """
    page_code = 'accounts_users'
    access_type = 'edit'

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        # Prevent disabling your own account or superadmin if needed
        if request.user == user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('accounts:user_list')

        user.is_active = not user.is_active
        user.save()

        # Audit log
        log_action(
            user=request.user,
            action='user_activated' if user.is_active else 'user_deactivated',
            instance=user,
            changes={'is_active': user.is_active},
            extra={'ip': self.request.META.get('REMOTE_ADDR')},
        )

        messages.success(
            request,
            f"User '{user.username}' has been {'activated' if user.is_active else 'deactivated'}."
        )
        return redirect('accounts:user_list')


class UserListView(PageAccessRequiredMixin, PagePermissionContextMixin, ListView):
    """
    Admin view: list all users.
    Requires 'accounts_users' page with at least 'view' access.
    """
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    page_code = 'accounts_users'
    access_type = 'view'

    def get_queryset(self):
        qs = super().get_queryset().select_related('created_by')

        user = self.request.user

        # If current user is NOT a superuser (by Django flag or by custom role),
        # hide all superuser accounts.
        if not (user.is_superuser or getattr(user, 'role', None) == 'superuser'):
            qs = qs.exclude(Q(is_superuser=True) | Q(role='superuser'))
        return qs


class UserCreateView(PageAccessRequiredMixin, FormInvalidMessageMixin, CreateView):
    """
    Admin view: create new user.
    Requires 'accounts_users' page with 'edit' (or higher) access.
    """
    model = User
    form_class = UserForm
    template_name = 'accounts/user_form.html'

    page_code = 'accounts_users'
    access_type = 'edit'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Set a default initial password
        form.instance.set_password(settings.DEFAULT_PASSWORD)

        response = super().form_valid(form)

        log_action(
            user=self.request.user,
            action='user_created',
            instance=self.object,
            changes=form.cleaned_data,
            extra={'ip': self.request.META.get('REMOTE_ADDR')}
        )

        messages.success(self.request, 'User created successfully.')
        return response

    def get_success_url(self):
        return reverse_lazy('accounts:user_list')


class UserUpdateView(PageAccessRequiredMixin, FormInvalidMessageMixin, UpdateView):
    """
    Admin view: update existing user.
    """
    model = User
    form_class = UserForm
    template_name = 'accounts/user_form.html'

    page_code = 'accounts_users'
    access_type = 'edit'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields.pop('username', None) # Remove username field in update form
        return form

    def form_valid(self, form):
        # Compare before/after values for audit trail
        old_instance = self.get_object()
        changed_fields = {}

        for field in form.changed_data:
            old_value = getattr(old_instance, field)
            new_value = form.cleaned_data.get(field)
            changed_fields[field] = {
                'old': str(old_value),
                'new': str(new_value)
            }

        response = super().form_valid(form)

        # Audit Logging
        log_action(
            user=self.request.user,
            action='user_updated',
            instance=self.object,
            changes=changed_fields,
            extra={'ip': self.request.META.get('REMOTE_ADDR')}
        )

        messages.success(self.request, 'User updated successfully.')
        return response

    def get_success_url(self):
        return reverse_lazy('accounts:user_list')


class RolePermissionListView(PageAccessRequiredMixin, TemplateView):
    """
    View to display and manage role-based page permissions.
    Superusers can manage all roles.
    Non-superusers cannot see or modify 'superuser' role permissions.
    """
    template_name = 'accounts/role_permissions.html'
    page_code = 'accounts_roles'
    access_type = 'view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pages = Page.objects.all().order_by('code')
        roles = User.ROLE_CHOICES  # [('superuser','SuperUser'), ('admin','Admin'), ('standard','Standard')]

        user = self.request.user

        # -------------------------------
        # 1. Restrict roles for non-superusers
        # -------------------------------
        if not (user.is_superuser or user.role == 'superuser'):
            # Filter out superuser from the roles list entirely
            roles = [r for r in roles if r[0] != 'superuser']

        # Build perm_map[role][page_id] = access_type
        perm_map: dict[str, dict] = {role: {} for role, _ in roles}

        for rp in RolePagePermission.objects.select_related('page'):
            if rp.role in perm_map:  # superuser perms won't be added for non-superusers
                perm_map[rp.role][rp.page_id] = rp.access_type

        context['pages'] = pages
        context['roles'] = roles
        context['perm_map'] = perm_map
        context['access_types'] = RolePagePermission.ACCESS_TYPES
        return context

    def post(self, request, *args, **kwargs):
        """
        Process form submission, preventing non-superusers
        from updating superuser permissions.
        """
        pages = Page.objects.all().order_by('code')
        all_roles = [r[0] for r in User.ROLE_CHOICES]
        user = request.user

        # -------------------------------------
        # 2. Non-superusers cannot modify superuser perms
        # -------------------------------------
        if not (user.is_superuser or user.role == 'superuser'):
            role_values = [r for r in all_roles if r != 'superuser']
        else:
            role_values = all_roles

        # Existing perms map: (role, page_id) -> rp instance
        existing = {
            (rp.role, rp.page_id): rp
            for rp in RolePagePermission.objects.all()
        }

        changes = {}

        for page in pages:
            for role in role_values:  # filtered roles list here
                field_name = f'perm_{role}_{page.id}'
                access_type = request.POST.get(field_name)

                # Ignore missing selects
                if not access_type:
                    continue

                key = (role, page.id)
                rp = existing.get(key)

                if rp:
                    if rp.access_type != access_type:
                        old = rp.access_type
                        rp.access_type = access_type
                        rp.save()
                        changes[f'{role}:{page.code}'] = {'old': old, 'new': access_type}
                else:
                    rp = RolePagePermission.objects.create(
                        role=role,
                        page=page,
                        access_type=access_type,
                    )
                    changes[f'{role}:{page.code}'] = {'old': None, 'new': access_type}

        if changes:
            log_action(
                user=request.user,
                action='role_permissions_updated',
                instance=None,
                changes=changes,
                extra={
                    'ip': request.META.get('REMOTE_ADDR'),
                },
            )
            messages.success(request, 'Role permissions updated successfully.')
        else:
            messages.info(request, 'No changes were made.')

        return redirect('accounts:role_permissions')


class UserPermissionUpdateView(PageAccessRequiredMixin, TemplateView):
    """
    View to manage per-user overrides (UserPagePermission).
    Admin can set view/edit/full/denied OR inherit role permissions.
    """
    template_name = 'accounts/user_permissions.html'
    page_code = 'accounts_users'
    access_type = 'full'  # only highest level can override

    def get_target_user(self):
        return get_object_or_404(User, pk=self.kwargs.get('pk'))

    def dispatch(self, request, *args, **kwargs):
        self.target_user = self.get_target_user()

        # Extra safety: only superusers can edit a superuser's permissions
        if (self.target_user.is_superuser or self.target_user.role == 'superuser') and not (
            request.user.is_superuser or request.user.role == 'superuser'
        ):
            raise PermissionDenied('You cannot modify a superuser permissions.')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pages = Page.objects.all().order_by('code')
        target_user = self.target_user

        # Existing per-user overrides
        user_perms = {
            perm.page.code: perm
            for perm in UserPagePermission.objects
                .filter(user=target_user)
                .select_related('page')
        }

        # Role-based default access for display
        role_defaults = {
            page.code: RolePagePermission.get_effective_access(target_user.role, page.code)
            for page in pages
        }

        context['target_user'] = target_user
        context['pages'] = pages
        context['user_permissions'] = user_perms
        context['role_defaults'] = role_defaults
        context['access_types'] = UserPagePermission.ACCESS_TYPES
        return context

    def post(self, request, *args, **kwargs):
        target_user = self.target_user
        pages = Page.objects.all().order_by('code')

        existing = {
            perm.page_id: perm
            for perm in UserPagePermission.objects.filter(user=target_user)
        }

        changes = {}

        for page in pages:
            field_name = f'perm_{page.id}'
            selected = request.POST.get(field_name)

            # nothing submitted for this page
            if selected is None:
                continue

            # 'inherit' means: remove override if exists
            if selected == 'inherit':
                perm = existing.get(page.id)
                if perm:
                    changes[page.code] = {'old': perm.access_type, 'new': 'inherit'}
                    perm.delete()
                continue

            # Otherwise, selected is one of 'view'/'edit'/'full'/'denied'
            perm = existing.get(page.id)
            if perm:
                if perm.access_type != selected:
                    changes[page.code] = {
                        'old': perm.access_type,
                        'new': selected,
                    }
                    perm.access_type = selected
                    perm.save()
            else:
                UserPagePermission.objects.create(
                    user=target_user,
                    page=page,
                    access_type=selected,
                    created_by=request.user,
                )
                changes[page.code] = {'old': 'inherit', 'new': selected}

        if changes:
            log_action(
                user=request.user,
                action='user_page_permissions_updated',
                instance=target_user,
                changes=changes,
                extra={'ip': request.META.get('REMOTE_ADDR')},
            )
            messages.success(request, 'User permissions updated successfully.')
        else:
            messages.info(request, 'No changes were made.')

        return redirect('accounts:user_permissions', pk=target_user.pk)

