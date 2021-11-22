from django.conf import settings
from djangae.environment import project_id as gae_project_id

import logging
import os
import grpc
from google.protobuf import field_mask_pb2

default_app_config = 'djangae.tasks.apps.DjangaeTasksConfig'

CLOUD_TASKS_PROJECT_SETTING = "CLOUD_TASKS_PROJECT_ID"
CLOUD_TASKS_LOCATION_SETTING = "CLOUD_TASKS_LOCATION"


def get_cloud_tasks_client():
    """
        Get an instance of a Google CloudTasksClient

        Note. Nested imports are to allow for things not to
        force the google cloud tasks dependency if you're not
        using it
    """
    from google.cloud.tasks import CloudTasksClient

    is_app_engine = os.environ.get("GAE_ENV") == "standard"

    if is_app_engine:
        return CloudTasksClient()
    else:
        # Running locally, try to connect to the emulator

        try:
            # google-cloud-tasks < 2.0.0 has this here
            from google.cloud.tasks_v2.gapic.transports.cloud_tasks_grpc_transport import CloudTasksGrpcTransport
        except ImportError:
            from google.cloud.tasks_v2.services.cloud_tasks.transports.grpc import CloudTasksGrpcTransport

        from google.api_core.client_options import ClientOptions

        host = os.environ.get("TASKS_EMULATOR_HOST", "127.0.0.1:9022")

        client = CloudTasksClient(
            transport=CloudTasksGrpcTransport(channel=grpc.insecure_channel(host)),
            client_options=ClientOptions(api_endpoint=host)
        )
        return client


def ensure_required_queues_exist():
    """
        Reads settings.CLOUD_TASK_QUEUES_REQUIRED
        and calls create_queue for them if they don't exist
    """
    client = get_cloud_tasks_client()
    parent_path = cloud_tasks_parent_path()

    for queue in getattr(settings, "CLOUD_TASKS_QUEUES", []):
        queue_name = queue["name"]

        # In our task settings we expect that the queue name will not
        # include the path, otherwise moving the app, changing location
        # etc. involves changing a load of settings.
        assert("/" not in queue_name)  # Don't specify the full path

        update_mask = ["name"]
        queue_dict = queue.copy()
        queue_dict["name"] = "%s/queues/%s" % (parent_path, queue_name)
        queue_dict["rateLimits"] = {}
        queue_dict["retryConfig"] = {}

        if "rate_per_second" in queue:
            update_mask.append("rateLimits.maxDispatchesPerSecond")
            queue_dict["rateLimits"]["maxDispatchesPerSecond"] = queue["rate_per_second"]

        if "rate_max_concurrent" in queue:
            update_mask.append("rateLimits.maxConcurrentDispatches")
            queue_dict["rateLimits"]["maxConcurrentDispatches"] = queue["rate_max_concurrent"]

        if "retry_max_attempts" in queue:
            update_mask.append("retryConfig.maxAttempts")
            queue_dict["retryConfig"]["maxAttempts"] = queue["retry_max_attempts"]

        logging.info("Ensuring task queue is up-to-date: %s", queue_dict["name"])

        client.update_queue(
            name=queue_dict["name"],
            queue=queue_dict,
            update_mask=field_mask_pb2.FieldMask(paths=update_mask)
        )


def cloud_tasks_project():
    project_id = getattr(settings, CLOUD_TASKS_PROJECT_SETTING, None)
    if not project_id:
        project_id = gae_project_id()

    return project_id


def cloud_tasks_location():
    location_id = getattr(settings, CLOUD_TASKS_LOCATION_SETTING, None)
    assert(location_id)
    return location_id


def cloud_tasks_parent_path():
    """
        Returns the path based on settings.CLOUD_TASK_PROJECT_ID
        and settings.CLOUD_TASK_LOCATION_ID. If these are
        unset, uses the project ID from the environment
    """

    location_id = getattr(settings, CLOUD_TASKS_LOCATION_SETTING, None)
    project_id = cloud_tasks_project()

    assert(project_id)
    assert(location_id)

    return "projects/%s/locations/%s" % (
        project_id, location_id
    )


def cloud_tasks_queue_path(queue_name, parent=None):
    """
        Returns a cloud tasks path to a queue, if parent
        is passed it uses that as a base, otherwise
        uses the result of cloud_tasks_parent_path()
    """

    return "%s/queues/%s" % (
        parent or cloud_tasks_parent_path(),
        queue_name
    )
