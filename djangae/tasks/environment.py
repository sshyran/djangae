import threading
from typing import Optional

from django.core.exceptions import ImproperlyConfigured

_TASK_ENV = threading.local()


def _check_task_environment_middleware():
    from django.conf import settings  # nested to prevent early-import

    check1 = "djangae.tasks.middleware.task_environment_middleware"
    check2 = "djangae.tasks.middleware.TaskEnvironmentMiddleware"

    enabled = any([x in settings.MIDDLEWARE for x in (check1, check2)])

    if not enabled:
        raise ImproperlyConfigured(
            "You must add djangae.tasks.middleware.TaskEnvironmentMiddleware "
            "to your MIDDLEWARE setting to make use of djangae.tasks.environment"
        )


def is_in_task() -> bool:
    "Returns True if the request is a task, False otherwise"
    _check_task_environment_middleware()
    return bool(getattr(_TASK_ENV, "task_name", False))


def is_in_cron() -> bool:
    "Returns True if the request is in a cron, False otherwise"
    _check_task_environment_middleware()
    return bool(getattr(_TASK_ENV, "is_cron", False))


def task_name() -> Optional[str]:
    "Returns the name of the current task if any, else None"
    _check_task_environment_middleware()
    return getattr(_TASK_ENV, "task_name", None)


def task_retry_count() -> Optional[int]:
    "Returns the task retry count, or None if this isn't a task"
    _check_task_environment_middleware()
    try:
        return int(getattr(_TASK_ENV, "task_retry_count", None))
    except (TypeError, ValueError):
        return None


def task_queue_name() -> Optional[str]:
    "Returns the name of the current task queue (if this is a task) else 'default'"
    _check_task_environment_middleware()
    if is_in_task():
        return getattr(_TASK_ENV, "queue_name", "default")
    return None


def task_execution_count() -> Optional[int]:
    _check_task_environment_middleware()
    if is_in_task():
        return getattr(_TASK_ENV, "task_execution_count", 0)
    return None


def tasks_location(app_id_with_prefix=None) -> Optional[str]:
    """
        Returns the cloud tasks location based on the application
        ID prefix. Returns None if unsuccessful. If no app_id
        is specified then it is read from the result of
        djangae.environment.application_id
    """

    from djangae.environment import application_id

    LOOKUP = {
        'b': 'asia-northeast1',
        'd': 'us-east4',
        'e': 'europe-west1',
        'f': 'australia-southeast',
        'g': 'europe-west2',
        'h': 'europe-west3',
        'i': 'southamerica-east1',
        'j': 'asia-south1',
        'k': 'northamerica-northeast1',
        'm': 'us-west2',
        'n': 'asia-east2',
        'o': 'europe-west6',
        'p': 'us-east1',
        's': 'us-central1',
        'u': 'asia-northeast2',
        'v': 'asia-northeast3',
        'zas': 'asia-southeast1',
        'zde': 'asia-east1',
        'zet': 'asia-southeast2',
        'zlm': 'europe-central2',
        'zuw': 'us-west1',
        'zwm': 'us-west3',
        'zwn': 'us-west4',
    }

    app_id_with_prefix = application_id() or app_id_with_prefix
    location_id = app_id_with_prefix.split("~", 1)[0]
    return LOOKUP.get(location_id)