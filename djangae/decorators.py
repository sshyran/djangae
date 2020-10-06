
from functools import wraps
from django.http import HttpResponseForbidden
from django.core.exceptions import ImproperlyConfigured


_TASK_NAME_HEADER = "HTTP_X_APPENGINE_TASKNAME"
_CRON_TASK_HEADER = "HTTP_X_APPENGINE_CRON"


def task_only(view_function):
    """ View decorator for restricting access to tasks (and crons) of the application
        only.
    """

    @wraps(view_function)
    def replacement(request, *args, **kwargs):

        is_in_task = bool(request.META.get(_TASK_NAME_HEADER, False))
        is_in_cron = bool(request.META.get(_CRON_TASK_HEADER, False))

        if not any((is_in_task, is_in_cron)):
            return HttpResponseForbidden("Access denied.")

        return view_function(request, *args, **kwargs)

    return replacement


def task_or_superuser_only(view_function):
    @wraps(view_function)
    def replacement(request, *args, **kwargs):
        is_superuser = (
            getattr(request, "user", None) and
            request.user.is_authenticated and
            request.user.is_superuser
        )

        is_in_task = bool(request.META.get(_TASK_NAME_HEADER, False))
        is_in_cron = bool(request.META.get(_CRON_TASK_HEADER, False))

        if not any((is_superuser, is_in_task, is_in_cron)):
            return HttpResponseForbidden("Access denied.")

        return view_function(request, *args, **kwargs)

    return replacement


def csrf_exempt_if_task(view_function):
    @wraps(view_function)
    def replacement(request, *args, **kwargs):
        return view_function(request, *args, **kwargs)

    class Replacement(object):
        def __call__(self, request, *args, **kwargs):
            view_function(request, *args, **kwargs)

        @property
        def csrf_exempt(self):
            from djangae.contrib.common import get_request
            request = get_request()

            if not request:
                raise ImproperlyConfigured(
                    "djangae.contrib.common.middleware.RequestStorageMiddleware "
                    "must be in your MIDDLEWARE setting ahead of CsrfMiddleware"
                )

            is_in_task = bool(request.META.get(_TASK_NAME_HEADER, False))
            is_in_cron = bool(request.META.get(_CRON_TASK_HEADER, False))

            return any((is_in_task, is_in_cron))

    return Replacement()
