from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ImproperlyConfigured


class PageAccessRequiredMixin(LoginRequiredMixin):
    """
    Enforce access to a logical 'Page' based on the custom permission system.

    Usage:
        class DoctorListView(PageAccessRequiredMixin, ListView):
            page_code = 'doctors'        # must match Page.code
            access_type = 'view'         # default
    """

    page_code = None
    access_type = 'view'  # 'view' | 'edit' | 'full'

    def get_page_code(self) -> str:
        """
        Resolve page_code. You can override this in subclasses if you want
        dynamic page codes.
        """

        code = self.page_code
        if not code:
            raise ImproperlyConfigured(
                f'{self.__class__.__name__} is missing a "page_code" attribute.'
            )
        return code

    def dispatch(self, request, *args, **kwargs):
        # LoginRequiredMixin will handle anonymous users
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # from LoginRequiredMixin

        page_code = self.get_page_code()
        if not page_code:
            raise ImproperlyConfigured('Missing page_code')

        if not request.user.has_page_access(page_code, self.access_type):
            raise PermissionDenied()

        return super().dispatch(request, *args, **kwargs)


class PagePermissionContextMixin:
    """
    Adds convenience flags to the template context:

        - can_view
        - can_edit
        - can_full

    Uses the same page_code resolution pattern as PageAccessRequiredMixin.

    Usage:
        class DoctorListView(PageAccessRequiredMixin,
                             PagePermissionContextMixin,
                             ListView):
            page_code = 'doctors'

            {% if can_edit %}
                <a href="{% url 'edit-doctor' doctor.id %}">Edit</a>
            {% endif %}
    """

    page_code = None

    def get_page_code(self) -> str:
        # Reuse same logic as in PageAccessRequiredMixin if both are mixed in
        if hasattr(super(), 'get_page_code'):
            try:
                return super().get_page_code()  # type: ignore[misc]
            except ImproperlyConfigured:
                pass

        code = self.page_code or getattr(self, 'PAGE_CODE', None)
        if not code:
            raise ImproperlyConfigured(
                f'{self.__class__.__name__} is missing a "page_code" attribute '
                'for PagePermissionContextMixin.'
            )
        return code

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_code = self.get_page_code()
        user = self.request.user

        context['can_view'] = user.has_page_access(page_code, 'view')
        context['can_edit'] = user.has_page_access(page_code, 'edit')
        context['can_full'] = user.has_page_access(page_code, 'full')

        return context
