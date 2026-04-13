"""Who may see / attach to a deployment task (align API + WebSockets)."""

from django.db.models import Q


def filter_deployment_tasks_for_user(queryset, user):
    if user is None or not user.is_authenticated:
        return queryset.none()
    if getattr(user, "is_staff", False):
        return queryset
    return queryset.filter(Q(created_by=user) | Q(created_by__isnull=True))


def get_deployment_task_for_user(task_id, user, select_related=None):
    from .models import DeploymentTask

    qs = DeploymentTask.objects.filter(pk=task_id)
    if select_related:
        qs = qs.select_related(*select_related)
    return filter_deployment_tasks_for_user(qs, user).first()
