from djangae.environment import is_production_environment

FILE_CACHE_LOCATION = '/tmp/cache' if is_production_environment() else '.cache'

CACHES = {
    # We default to the filesystem cache, since it's quick and easy for simple app
    # For larger application you should consider Cloud Memory Store (which does not have a free tier)
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': FILE_CACHE_LOCATION,
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'djangae': {
            'level': 'WARN'
        }
    }
}

# Setting to * is OK, because GAE takes care of domain routing - setting it to anything
# else just causes unnecessary pain when something isn't accessible under a custom domain
ALLOWED_HOSTS = ("*",)


# We set this default because Cloud Datastore uses signed 64 bit integers for IDs
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Set a default CLOUD_TASKS_LOCATION variable based on the environment (if we can)
from djangae.tasks.environment import tasks_location
CLOUD_TASKS_LOCATION = tasks_location()