from django.shortcuts import redirect
from django.views.generic.edit import CreateView, UpdateView
from django.contrib import messages

from audit.models import log_action


class AuditLogFormValidMixin:
    action = None               # 'create' or 'update' (optional)
    success_message = None      # per view

    def get_client_ip(self):
        return self.request.META.get('REMOTE_ADDR')

    def get_action(self):
        if self.action:
            return self.action
        # Default based on CBV type
        if isinstance(self, CreateView):
            return 'create'
        if isinstance(self, UpdateView):
            return 'update'
        return 'update'

    def get_success_message(self):
        return self.success_message

    def build_changes_for_create(self, form):
        # snapshot
        return dict(form.cleaned_data)

    def build_changes_for_update(self, form):
        # diff
        old_instance = self.get_object()
        changes = {}
        for field in form.changed_data:
            changes[field] = {
                'old': getattr(old_instance, field, None),
                'new': form.cleaned_data.get(field),
            }
        return changes

    def build_changes(self, form):
        action = self.get_action()
        if action == 'create':
            return self.build_changes_for_create(form)
        return self.build_changes_for_update(form)

    def write_audit_log(self, *, instance, changes):
        log_action(
            user=self.request.user,
            action=self.get_action(),
            instance=instance,
            changes=changes,
            extra={'ip': self.get_client_ip()},
        )

    def form_valid(self, form):
        # For update, get_object() must be called before save to capture 'old'.
        # For create, build_changes_for_create doesn't call get_object().
        changes = self.build_changes(form)

        response = super().form_valid(form)  # saves; sets self.object

        self.write_audit_log(instance=self.object, changes=changes)

        msg = self.get_success_message()
        if msg:
            messages.success(self.request, msg)

        return response


class FormInvalidMessageMixin:
    """
    Mixin to display Django form validation errors via messages framework.
    """
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    messages.error(self.request, error)
                else:
                    messages.error(self.request, f'{field}: {error}')

        return super().form_invalid(form)


class RedirectFormInvalidMessageMixin:
    """
    Use on POST-only FormView endpoints that redirect instead of rendering templates.
    """

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field}: {error}')

        # Redirect back to where the request came from
        return redirect(self.request.META.get('HTTP_REFERER', '/'))
