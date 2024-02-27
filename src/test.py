import os
import sys
import time
import asyncio
import logging
import datetime
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.client import V1Deployment, V1StatefulSet
import kopf

config.load_kube_config()

LOG_FORMAT = '%(asctime)s [%(levelname)s]: %(message)s'
LOG_LEVEL = logging.INFO
logger = logging.getLogger('base')
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(handler)

ANNOTATION_KEY_ENABLED = os.getenv('ANNOTATION_KEY_ENABLED')
ANNOTATION_KEY_ON_TIME = os.getenv('ANNOTATION_KEY_ON_TIME') # annotation key used to specify the off-time
ANNOTATION_KEY_OFF_TIME = os.getenv('ANNOTATION_KEY_OFF_TIME') # annotation key used to specify the off-time
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL'))


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **kwargs):
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage()


@kopf.on.timer('statefulsets', interval=CHECK_INTERVAL, annotations={ANNOTATION_KEY_ENABLED: "true"})
def check_off_time(**kwargs):
    api_client = client.ApiClient()
    api_instance = client.AppsV1Api(api_client)

    try:
        # StatefulSets
        statefulsets = api_instance.list_stateful_set_for_all_namespaces().items

        # Check off-time for StatefulSets
        for statefulset in statefulsets:
            annotations = statefulset.metadata.annotations
            if annotations:
                off_time = annotations.get(ANNOTATION_KEY_OFF_TIME)
                if off_time and is_off_time(off_time):
                    set_replica_count(statefulset, 0)

    except ApiException as e:
        logger.error("Exception when calling AppsV1Api: %s\n" % e)

@kopf.on.timer('deployments', interval=CHECK_INTERVAL, annotations={ANNOTATION_KEY_ENABLED: "true"})
def check_off_time(**kwargs):
    api_client = client.ApiClient()
    api_instance = client.AppsV1Api(api_client)

    try:
        # Deployments
        deployments = api_instance.list_deployment_for_all_namespaces().items

        # Check off-time for Deployments
        for deployment in deployments:
            annotations = deployment.metadata.annotations
            if annotations:
                off_time = annotations.get(ANNOTATION_KEY_OFF_TIME)
                if off_time and is_off_time(off_time):
                    set_replica_count(deployment, 0)

    except ApiException as e:
        logger.error("Exception when calling AppsV1Api: %s\n" % e)


def is_off_time(off_time):
    current_time = datetime.datetime.now().time()
    off_time_hour, off_time_minute = map(int, off_time.split(":"))
    off_time_dt = datetime.time(off_time_hour, off_time_minute)

    if current_time >= off_time_dt:
        return True
    else:
        return False


def set_replica_count(obj, replica_count):
    api_client = client.ApiClient()
    api_instance = client.AppsV1Api(api_client)

    if isinstance(obj, V1Deployment):
        obj.spec.replicas = replica_count
        api_instance.patch_namespaced_deployment(
            obj.metadata.name,
            obj.metadata.namespace,
            obj
        )
        logger.info(f"Deployment {obj.metadata.namespace}/{obj.metadata.name} off-time reached and scaled to 0")

    elif isinstance(obj, V1StatefulSet):
        obj.spec.replicas = replica_count
        api_instance.patch_namespaced_stateful_set(
            obj.metadata.name,
            obj.metadata.namespace,
            obj
        )
        logger.info(f"StatefulSet {obj.metadata.namespace}/{obj.metadata.name} off-time reached and scaled to 0")


def main(argv):
    loop = asyncio.get_event_loop()

    # Priority defines the priority/weight of this instance of the operator for
    # kopf peering. If there are multiple operator instances in the cluster,
    # only the one with the highest priority will actually be active.
    loop.run_until_complete(kopf.operator(
        clusterwide=True,
        priority=int(time.time()*1000000),
        peering_name="tbro-operator" # must be the same as the identified in ClusterKopfPeering
    ))

    return 0


if __name__ == "__main__":
    main([])