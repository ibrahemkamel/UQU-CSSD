from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

from cssd.views import (
    home,
    dashboard,
    new_request,
    get_template_items,
    cssd_pending_requests,
    cssd_request_details,
    cssd_received_requests,
    return_to_clinic,
    clinic_pending_returns,
    confirm_by_clinic,
    close_request,
    print_request,
    all_requests,
    notifications,
    reports,
    my_requests,
    clinic_confirm_details,
)

urlpatterns = [

    path('admin/', admin.site.urls),

    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='cssd/login.html'
        ),
        name='login'
    ),

    path(
        'logout/',
        auth_views.LogoutView.as_view(
            next_page='login'
        ),
        name='logout'
    ),

    path('', dashboard, name='dashboard'),

    path('home/', home, name='home'),

    path('new-request/', new_request, name='new_request'),

    path(
        'get-template-items/<int:template_id>/',
        get_template_items,
        name='get_template_items'
    ),

    path(
        'cssd-pending/',
        cssd_pending_requests,
        name='cssd_pending_requests'
    ),

    path(
        'cssd-request/<int:request_id>/',
        cssd_request_details,
        name='cssd_request_details'
    ),

    path(
        'cssd-received/',
        cssd_received_requests,
        name='cssd_received_requests'
    ),

    path(
        'return-to-clinic/<int:request_id>/',
        return_to_clinic,
        name='return_to_clinic'
    ),

    path(
        'clinic-pending-returns/',
        clinic_pending_returns,
        name='clinic_pending_returns'
    ),
    path(
    'clinic-confirm-details/<int:request_id>/',
    clinic_confirm_details,
    name='clinic_confirm_details'
    ),

    path(
        'confirm-by-clinic/<int:request_id>/',
        confirm_by_clinic,
        name='confirm_by_clinic'
    ),

    path(
        'close-request/<int:request_id>/',
        close_request,
        name='close_request'
    ),

    path(
        'print-request/<int:request_id>/',
        print_request,
        name='print_request'
    ),
    path(
    'all-requests/',
    all_requests,
    name='all_requests'
),

path(
    'notifications/',
    notifications,
    name='notifications'
),

path(
    'reports/',
    reports,
    name='reports'
),
path(
    'my-requests/',
    my_requests,
    name='my_requests'
),

]