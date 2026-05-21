from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf.urls import handler403, handler404, handler500

from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView

# --- Custom 403 handler ---
def custom_permission_denied_view(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def custom_page_not_found_view(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def custom_server_error_view(request):
    return render(request, 'errors/500.html', status=500)


handler403 = custom_permission_denied_view
handler404 = custom_page_not_found_view
handler500 = custom_server_error_view


urlpatterns = [
    path('', include('dashboard.urls', namespace='dashboard')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('audit/', include('audit.urls', namespace='audit')),
    path('admin/', admin.site.urls),

    path('sales/', include('sales.urls', namespace='sales')),

    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('images/favicon.ico'))),
]
