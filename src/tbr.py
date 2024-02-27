import os
import time
import kopf
import asyncio
from kubernetes import client
from kubernetes import config
from datetime import datetime
from pytz import timezone, utc
from typing import Optional, Dict

# config.load_incluster_config()
config.load_kube_config()
v1 = client.AppsV1Api()
custom_api = client.CustomObjectsApi()

API_GROUP = 'abriment.dev'
API_VERSION = 'v1'

CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL'))

POLICY_NAME_ANNOTATION_KEY = f'tbr.{API_GROUP}/policy'
REPLICAS_ANNOTATION_KEY = f'tbr.{API_GROUP}/replicas'


def get_tbr(ns, tbr_policy: str, logger) -> Optional[Dict]:
    try:
        tbr = custom_api.get_namespaced_custom_object(
            group=API_GROUP,
            version=API_VERSION,
            plural='tbrs',
            name=tbr_policy,
            namespace=ns
        )
        return tbr
    except client.exceptions.ApiException as e:
        if e.status == 404:
            logger.warning(f"TBR {tbr_policy} not found")
        else:
            logger.error(f"Failed to get TBR {tbr_policy}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None


@kopf.timer('deployments',
            interval=CHECK_INTERVAL,
            annotations={POLICY_NAME_ANNOTATION_KEY: kopf.PRESENT},
            )
async def deployment_timer_handler(meta: Dict, spec: Dict, **kwargs):
    obj_type = 'deployment'
    logger = kwargs['logger']
    current_replicas = spec.get('replicas')

    ns = meta['namespace']
    name = meta['name']
    tbr_policy = meta['annotations'][POLICY_NAME_ANNOTATION_KEY]
    logger.info(f"Deployment {ns}/{name} has TBR {tbr_policy}")

    tbr = get_tbr(ns, tbr_policy, logger)
    if not tbr:
        return

    start_time = tbr['spec']['startTime']
    end_time = tbr['spec']['endTime']
    tbr_tz = tbr['spec']['timeZone']

    current_time_obj = datetime.now(timezone(tbr_tz)).time()
    logger.info(f"Current time in {tbr_tz}: {current_time_obj}")

    start_time_obj = datetime.strptime(start_time, '%H:%M').time()
    end_time_obj = datetime.strptime(end_time, '%H:%M').time()

    logger.debug(
        f"TBR working hours: {start_time_obj}-{end_time_obj}")

    try:
        if end_time_obj < start_time_obj:
            logger.error(f'endTime {end_time_obj} value cannot be earlier than startTime {start_time_obj}')
            return
        
        if end_time_obj == start_time_obj:
            logger.error(f'endTime {end_time_obj} value cannot be equal to startTime {start_time_obj}')
            return
        
        if current_time_obj < start_time_obj or current_time_obj > end_time_obj:
            logger.info(
                f"Current time {current_time_obj} is outside the working hours {start_time_obj}-{end_time_obj}")
            go_to_sleep(obj_type, meta, current_replicas, logger)
        else:
            logger.info(
                f"Current time {current_time_obj} is within the working hours {start_time_obj}-{end_time_obj}")
            wake_up(obj_type, meta, current_replicas, logger)
    except Exception as e:
        logger.error(f"Failed to process TBR: {e}")
        return

    return

@kopf.timer('statefulsets',
            interval=CHECK_INTERVAL,
            annotations={POLICY_NAME_ANNOTATION_KEY: kopf.PRESENT},
            )
async def statefulset_timer_handler(meta: Dict, spec: Dict, **kwargs):
    obj_type = 'statefulset'
    logger = kwargs['logger']
    current_replicas = spec.get('replicas')

    ns = meta['namespace']
    name = meta['name']
    tbr_policy = meta['annotations'][POLICY_NAME_ANNOTATION_KEY]
    logger.info(f"Statefulset {ns}/{name} has TBR {tbr_policy}")

    tbr = get_tbr(ns, tbr_policy, logger)
    if not tbr:
        return

    start_time = tbr['spec']['startTime']
    end_time = tbr['spec']['endTime']
    tbr_tz = tbr['spec']['timeZone']

    current_time_obj = datetime.now(timezone(tbr_tz)).time()
    logger.info(f"Current time in {tbr_tz}: {current_time_obj}")

    start_time_obj = datetime.strptime(start_time, '%H:%M').time()
    end_time_obj = datetime.strptime(end_time, '%H:%M').time()

    logger.debug(
        f"TBR working hours: {start_time_obj}-{end_time_obj}")

    try:
        if end_time_obj < start_time_obj:
            logger.error(f'endTime {end_time_obj} value cannot be earlier than startTime {start_time_obj}')
            return
        
        if end_time_obj == start_time_obj:
            logger.error(f'endTime {end_time_obj} value cannot be equal to startTime {start_time_obj}')
            return
        
        if current_time_obj < start_time_obj or current_time_obj > end_time_obj:
            logger.info(
                f"Current time {current_time_obj} is outside the working hours {start_time_obj}-{end_time_obj}")
            go_to_sleep(obj_type, meta, current_replicas, logger)
        else:
            logger.info(
                f"Current time {current_time_obj} is within the working hours {start_time_obj}-{end_time_obj}")
            wake_up(obj_type, meta, current_replicas, logger)
    except Exception as e:
        logger.error(f"Failed to process TBR: {e}")
        return

    return


def go_to_sleep(obj_type, meta: Dict, current_replicas: int, logger):
    if current_replicas == 0:
        logger.debug(
            f"{obj_type.title()} is already scaled down")
        return

    logger.info(
        f"Scaling down {obj_type.title()}")

    logger.debug(
        f"Storing current replica count {current_replicas} in the annotations")
    patch_resource(
        obj_type=obj_type,
        name=meta['name'],
        namespace=meta['namespace'],
        body={
            "metadata": {
                "annotations": {
                    REPLICAS_ANNOTATION_KEY: str(current_replicas)
                }
            }
        },
        logger=logger
    )

    return patch_resource(
        obj_type=obj_type,
        name=meta['name'],
        namespace=meta['namespace'],
        body={
            "spec": {
                "replicas": 0
            }
        },
        logger=logger
    )

def wake_up(obj_type, meta: Dict, current_replicas: int, logger):
    if current_replicas > 0:
        logger.debug(
            f"{obj_type.title()} is already scaled up")
        return

    replicas = int(meta['annotations'][REPLICAS_ANNOTATION_KEY])
    logger.info(
        f"Scaling up {obj_type.title()} to the previous replica count: {replicas}")

    return patch_resource(
        obj_type=obj_type,
        name=meta['name'],
        namespace=meta['namespace'],
        body={
            "spec": {
                "replicas": replicas
            }
        },
        logger=logger
    )


def patch_resource(obj_type, name: str, namespace: str, body: Dict, logger):
    try:
        if obj_type == 'deployment':
            v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body
            )

        if obj_type == 'statefulset':
            v1.patch_namespaced_stateful_set(
                name=name,
                namespace=namespace,
                body=body
            ) 

        logger.debug(
            f"Successfully patched {obj_type.title()} {name} in namespace {namespace}")

    except client.exceptions.ApiException as e:
        logger.error(
            f"Failed to patch {obj_type.title()} {name} in namespace {namespace}: {e}")

    except Exception as e:
        logger.error(
            f"An unexpected error occurred while patching {obj_type.title()}: {e}")

@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, logger, **_):
    settings.persistence.finalizer = f'finalizers.{API_GROUP}/tbr-cleanup'

def main(argv):
    loop = asyncio.get_event_loop()

    # Priority defines the priority/weight of this instance of the operator for
    # kopf peering. If there are multiple operator instances in the cluster,
    # only the one with the highest priority will actually be active.
    loop.run_until_complete(kopf.operator(
        clusterwide=True,
        priority=int(time.time()*1000000),
        peering_name="tbr-operator" # must be the same as the identified in ClusterKopfPeering
    ))

    return 0


if __name__ == "__main__":
    main([])