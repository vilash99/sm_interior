from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    path('profile/', views.ProfileView.as_view(), name='profile'),

    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),

    # Admin-style
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/add/', views.UserCreateView.as_view(), name='user_add'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/permissions/', views.UserPermissionUpdateView.as_view(), name='user_permissions'),
    path('users/<int:pk>/toggle-status/', views.UserToggleStatusView.as_view(), name='user_toggle_status'),

    path('roles/permissions/', views.RolePermissionListView.as_view(), name='role_permissions'),
]
