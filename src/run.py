from redis import Redis
from rq import Queue, Connection
import json
import logger
import os
import requests


def __main__():
    # Fetch connection information
    REDIS_HOST = os.environ.get('REDIS_HOST')
    REDIS_PORT = os.environ.get('REDIS_PORT')

    with Connection(Redis(REDIS_HOST, REDIS_PORT)):
        # Iterate the queues, and check the length
        for queue_name, threshold in get_queues_and_thresholds():
            q = Queue(queue_name)
            queue_length = len(q)
            if queue_length >= threshold:
                send_alert(queue_name, queue_length)


if __name__ == "__main__":
    __main__()


def get_queues_and_thresholds():
    """
    Returns a list of 2-tuples, where the first item is the queue name and the
    second item is the notification threshold.
    """
    QUEUE_THRESHOLDS = json.loads(os.environ.get('QUEUE_THRESHOLDS', ''))
    return QUEUE_THRESHOLDS.values()


def send_alert(queue_name, queue_length):
    """
    Send an alert via slack to a specific webhook address notifying users of the
    queue length.
    """
    SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

    if not SLACK_WEBHOOK_URL:
        logger.warning('SLACK_WEBHOOK_URL was not found in the environment, no alert will be sent.')
        return
    payload = {'text': '%s queue length alert - %d' % (queue_name, queue_length)}
    requests.post(SLACK_WEBHOOK_URL, json=payload)
