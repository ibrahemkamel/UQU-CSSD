from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count

import qrcode
import base64
from io import BytesIO

from .models import Notification

@login_required
def notifications(request):

    user_groups = list(
        request.user.groups.values_list("name", flat=True)
    )

    notifications = Notification.objects.filter(
        target_group__in=user_groups
    ).order_by("-created_at")

    # تصفير الإشعارات غير المقروءة
    Notification.objects.filter(
        target_group__in=user_groups,
        is_read=False
    ).update(is_read=True)

    return render(
        request,
        "cssd/notifications.html",
        {
            "notifications": notifications
        }
    )

from .forms import NewCSSDRequestForm
from .models import (
    CSSDTemplate,
    CSSDTemplateItem,
    CSSDRequest,
    CSSDRequestTemplate,
    CSSDRequestItem,
    Notification,
)


def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def is_admin(user):
    return user.is_superuser or user_in_group(user, "ADMIN")


def is_cssd(user):
    return user_in_group(user, "CSSD")


def user_location_groups(user):
    groups = ["MALE", "FEMALE", "SPECIALTY", "EMERGENCY"]
    return [g for g in groups if user_in_group(user, g)]


def visible_requests_for_user(user):
    if is_admin(user) or is_cssd(user):
        return CSSDRequest.objects.all()

    user_groups = user_location_groups(user)
    return CSSDRequest.objects.filter(location__group_type__in=user_groups)


def can_access_request(user, cssd_request):
    if is_admin(user) or is_cssd(user):
        return True

    return cssd_request.location.group_type in user_location_groups(user)


@login_required
def home(request):
    return redirect("dashboard")


@login_required
def dashboard(request):
    requests_qs = visible_requests_for_user(request.user)

    total_requests = requests_qs.count()
    pending_requests = requests_qs.filter(status="SENT_TO_CSSD").count()
    received_requests = requests_qs.filter(status="RECEIVED_BY_CSSD").count()
    returned_requests = requests_qs.filter(status="RETURNED_TO_CLINIC").count()
    confirmed_requests = requests_qs.filter(status="CONFIRMED_BY_CLINIC").count()
    closed_requests = requests_qs.filter(status="CLOSED").count()
    latest_requests = requests_qs.order_by("-created_at")[:5]

    return render(request, "cssd/dashboard.html", {
    "total_requests": total_requests,
    "pending_requests": pending_requests,
    "received_requests": received_requests,
    "returned_requests": returned_requests,
    "confirmed_requests": confirmed_requests,
    "closed_requests": closed_requests,
    "latest_requests": latest_requests,

    "is_cssd_user": is_cssd(request.user),
    "is_admin_user": is_admin(request.user),
    "is_clinic_user": bool(user_location_groups(request.user)),
})


@login_required
def new_request(request):
    form = NewCSSDRequestForm()

    if request.method == "POST":
        location_id = request.POST.get("location")
        procedure_note = request.POST.get("procedure", "")

        cssd_request = CSSDRequest.objects.create(
            location_id=location_id,
            procedure=procedure_note,
            created_by=request.user,
            status="SENT_TO_CSSD"
        )

        if not can_access_request(request.user, cssd_request):
            cssd_request.delete()
            return HttpResponseForbidden("You are not allowed to create request for this location.")

        used_templates = []

        for key, template_id in request.POST.items():
            if key.startswith("template_") and template_id:
                index = key.split("_")[1]
                template = get_object_or_404(CSSDTemplate, id=template_id)

                request_template = CSSDRequestTemplate.objects.create(
                    cssd_request=cssd_request,
                    template=template
                )

                used_templates.append(template.name)
                prefix = f"qty_{index}_"

                for qty_key, qty_value in request.POST.items():
                    if qty_key.startswith(prefix):
                        item_id = qty_key.replace(prefix, "")
                        quantity = int(qty_value or 0)

                        if quantity > 0:
                            item = get_object_or_404(CSSDTemplateItem, id=item_id)

                            CSSDRequestItem.objects.create(
                                cssd_request=cssd_request,
                                cssd_request_template=request_template,
                                instrument_name=item.instrument_name,
                                quantity_sent=quantity,
                                is_manual=False
                            )

        manual_names = request.POST.getlist("manual_name[]")
        manual_quantities = request.POST.getlist("manual_qty[]")

        for name, qty in zip(manual_names, manual_quantities):
            name = name.strip()
            quantity = int(qty or 0)

            if name and quantity > 0:
                CSSDRequestItem.objects.create(
                    cssd_request=cssd_request,
                    cssd_request_template=None,
                    instrument_name=name,
                    quantity_sent=quantity,
                    is_manual=True
                )

        Notification.objects.create(
            target_group="CSSD",
            title="New CSSD Request",
            message=f"New request from {cssd_request.location.name}: {', '.join(used_templates)}",
            cssd_request=cssd_request
        )

        return redirect("cssd_pending_requests")

    templates = CSSDTemplate.objects.all()

    return render(request, "cssd/new_request.html", {
        "form": form,
        "templates": templates,
    })


@login_required
def get_template_items(request, template_id):
    items = CSSDTemplateItem.objects.filter(
        template_id=template_id
    ).order_by("sort_order").values("id", "instrument_name")

    return JsonResponse(list(items), safe=False)


@login_required
def cssd_pending_requests(request):
    requests = visible_requests_for_user(request.user).filter(
        status="SENT_TO_CSSD"
    ).order_by("-created_at")

    return render(request, "cssd/cssd_pending.html", {"requests": requests})


@login_required
def cssd_request_details(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to access this request.")

    if request.method == "POST":
        if not (is_admin(request.user) or is_cssd(request.user)):
            return HttpResponseForbidden("Only CSSD can receive requests.")

        for item in cssd_request.items.all():
            received_qty = request.POST.get(f"received_{item.id}", 0)
            comment = request.POST.get(f"comment_{item.id}", "")

            item.quantity_received_by_cssd = int(received_qty or 0)
            item.remarks = comment
            item.save()

        cssd_request.status = "RECEIVED_BY_CSSD"
        cssd_request.received_by = request.user
        cssd_request.received_at = timezone.now()
        cssd_request.save()

        Notification.objects.create(
            target_group=cssd_request.location.group_type,
            title="CSSD Received Request",
            message=f"CSSD received request #{cssd_request.id}",
            cssd_request=cssd_request
        )

        return redirect("cssd_pending_requests")

    return render(request, "cssd/request_details.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
    })


@login_required
def cssd_received_requests(request):
    requests = visible_requests_for_user(request.user).filter(
        status="RECEIVED_BY_CSSD"
    ).order_by("-created_at")

    return render(request, "cssd/cssd_received.html", {"requests": requests})


@login_required
def return_to_clinic(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to access this request.")

    if request.method == "POST":
        if not (is_admin(request.user) or is_cssd(request.user)):
            return HttpResponseForbidden("Only CSSD can return requests.")

        for item in cssd_request.items.all():
            returned_qty = request.POST.get(f"returned_{item.id}", 0)
            item.quantity_returned = int(returned_qty or 0)
            item.save()

        cssd_request.status = "RETURNED_TO_CLINIC"
        cssd_request.returned_by = request.user
        cssd_request.returned_at = timezone.now()
        cssd_request.save()

        Notification.objects.create(
            target_group=cssd_request.location.group_type,
            title="Instruments Returned",
            message=f"CSSD returned request #{cssd_request.id} to clinic",
            cssd_request=cssd_request
        )

        return redirect("cssd_received_requests")

    return render(request, "cssd/return_to_clinic.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
    })


@login_required
def clinic_pending_returns(request):
    requests = visible_requests_for_user(request.user).filter(
        status="RETURNED_TO_CLINIC"
    ).order_by("-created_at")

    return render(request, "cssd/clinic_pending_returns.html", {"requests": requests})


@login_required
def confirm_by_clinic(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to access this request.")

    if is_cssd(request.user) and not is_admin(request.user):
        return HttpResponseForbidden("CSSD cannot confirm clinic receipt.")

    cssd_request.status = "CLOSED"
    cssd_request.closed_by = request.user
    cssd_request.closed_at = timezone.now()
    cssd_request.save()

    Notification.objects.create(
        target_group="CSSD",
        title="Clinic Confirmed Receipt",
        message=f"Clinic confirmed receiving request #{cssd_request.id}",
        cssd_request=cssd_request
    )

    return redirect("clinic_pending_returns")


@login_required
def close_request(request, request_id):
    if not is_admin(request.user):
        return HttpResponseForbidden("Only Admin can close requests.")

    cssd_request = get_object_or_404(CSSDRequest, id=request_id)
    cssd_request.status = "CLOSED"
    cssd_request.closed_by = request.user
    cssd_request.closed_at = timezone.now()
    cssd_request.save()

    return redirect("clinic_pending_returns")


@login_required
def print_request(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to print this request.")

    request_url = request.build_absolute_uri(
        f"/cssd-request/{cssd_request.id}/"
    )

    qr = qrcode.make(request_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    qr_code = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "cssd/print_request.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
        "qr_code": qr_code,
        "request_url": request_url,
    })
@login_required
def all_requests(request):
    requests = visible_requests_for_user(request.user)

    search = request.GET.get("search", "")
    status = request.GET.get("status", "")

    if search:
        requests = requests.filter(
            location__name__icontains=search
        ) | requests.filter(
            created_by__username__icontains=search
        ) | requests.filter(
            id__icontains=search
        )

    if status:
        requests = requests.filter(status=status)

    requests = requests.order_by("-created_at")

    return render(request, "cssd/all_requests.html", {
        "requests": requests,
        "search": search,
        "status": status,
    })
@login_required
def reports(request):

    requests_qs = visible_requests_for_user(request.user)

    total_requests = requests_qs.count()
    pending_requests = requests_qs.filter(status="SENT_TO_CSSD").count()
    received_requests = requests_qs.filter(status="RECEIVED_BY_CSSD").count()
    returned_requests = requests_qs.filter(status="RETURNED_TO_CLINIC").count()
    closed_requests = requests_qs.filter(status="CLOSED").count()

    locations = requests_qs.values(
        "location__name"
    ).annotate(
        total=Count("id")
    ).order_by("-total")

    users = requests_qs.values(
        "created_by__username"
    ).annotate(
        total=Count("id")
    ).order_by("-total")

    return render(request, "cssd/reports.html", {
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "received_requests": received_requests,
        "returned_requests": returned_requests,
        "closed_requests": closed_requests,
        "locations": locations,
        "users": users,
    })
@login_required
def my_requests(request):
    requests = CSSDRequest.objects.filter(
        created_by=request.user
    ).order_by("-created_at")

    return render(request, "cssd/my_requests.html", {
        "requests": requests
    })


@login_required
def clinic_confirm_details(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to access this request.")

    if cssd_request.status != "RETURNED_TO_CLINIC":
        return HttpResponseForbidden("This request is not ready for clinic confirmation.")

    if is_cssd(request.user) and not is_admin(request.user):
        return HttpResponseForbidden("CSSD cannot confirm clinic receipt.")

    if request.method == "POST":
        cssd_request.status = "CLOSED"
        cssd_request.closed_by = request.user
        cssd_request.closed_at = timezone.now()
        cssd_request.save()

        Notification.objects.create(
            target_group="CSSD",
            title="Clinic Confirmed Receipt",
            message=f"Clinic confirmed receiving request #{cssd_request.id}",
            cssd_request=cssd_request
        )

        return redirect("clinic_pending_returns")

    return render(request, "cssd/clinic_confirm_details.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
    })