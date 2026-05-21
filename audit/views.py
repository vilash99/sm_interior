from django.views.generic import ListView
from django.db.models import Q
from django.contrib.auth import get_user_model

from accounts.mixins import PageAccessRequiredMixin, PagePermissionContextMixin
from audit.models import AuditLog


User = get_user_model()

class AuditLogListView(PageAccessRequiredMixin, PagePermissionContextMixin, ListView):
    """
    Admin view: list audit logs with simple filters.
    Requires 'accounts_audit_logs' page with at least 'view' access.
    """
    model = AuditLog
    template_name = 'audit/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 30

    page_code = 'audit_logs'
    access_type = 'view'

    def get_queryset(self):
        qs = super().get_queryset().select_related('user').order_by('-created_at')

        request = self.request
        user_id = request.GET.get('user')
        action = request.GET.get('action')
        model_name = request.GET.get('model')
        search = request.GET.get('q')

        if user_id:
            qs = qs.filter(user_id=user_id)

        if action:
            qs = qs.filter(action__iexact=action)

        if model_name:
            qs = qs.filter(model_name__iexact=model_name)

        if search:
            qs = qs.filter(
                Q(action__icontains=search)
                | Q(model_name__icontains=search)
                | Q(object_id__icontains=search)
                | Q(user__username__icontains=search)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # For filter dropdowns
        context['users'] = User.objects.order_by('username')
        context['selected_user'] = self.request.GET.get('user') or ''
        context['selected_action'] = self.request.GET.get('action') or ''
        context['selected_model'] = self.request.GET.get('model') or ''
        context['search_query'] = self.request.GET.get('q') or ''

        # Distinct actions/models for simple filters
        context['actions'] = (
            AuditLog.objects.values_list('action', flat=True)
            .distinct()
            .order_by('action')
        )
        context['models'] = (
            AuditLog.objects.values_list('model_name', flat=True)
            .distinct()
            .order_by('model_name')
        )

        return context

