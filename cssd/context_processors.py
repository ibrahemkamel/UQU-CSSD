from .models import Notification


def notification_count(request):
    if not request.user.is_authenticated:
        return {
            "unread_notifications_count": 0
        }

    user_groups = list(
        request.user.groups.values_list("name", flat=True)
    )

    count = Notification.objects.filter(
        target_group__in=user_groups,
        is_read=False
    ).count()

    return {
        "unread_notifications_count": count
    }