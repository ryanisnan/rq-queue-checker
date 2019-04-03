from rq import Queue
import json
import logging
import os
import redis
import requests
import sys
import uuid


base_logger = logging.getLogger(__name__)
base_logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

base_logger.addHandler(handler)


class LoggingTransactionAdapter(logging.LoggerAdapter):
    """
    Add a transaction ID to each log message corresponding this adapter.
    Used for instrumenting a request (aka transaction)'s log messages with
    a unique UUID for monitoring purposes.
    """
    def __init__(self, *args, **kwargs):
        setattr(self, 'trn_id', str(uuid.uuid4()))
        kwargs['extra'] = {}
        super().__init__(*args, **kwargs)

    def process(self, msg, kwargs):
        return '[trn: %s] %s' % (getattr(self, 'trn_id'), msg), kwargs


def get_queues_and_thresholds(logger):
    """
    Returns a list of 2-tuples, where the first item is the queue name and the
    second item is the notification threshold.
    """
    QUEUE_THRESHOLDS = os.environ.get('QUEUE_THRESHOLDS', '{}')
    logger.debug('Queue configuration: %s' % QUEUE_THRESHOLDS)

    try:
        queues_and_thresholds = json.loads(QUEUE_THRESHOLDS)
    except:
        logger.error('Could not parse queue configuration as JSON')
        exit()

    return queues_and_thresholds.items()


def __main__():
    logger = LoggingTransactionAdapter(base_logger)
    logger.debug('Running queue checker')

    # Fetch connection information - ensure it has been set
    REDIS_HOST = os.environ.get('REDIS_HOST')
    REDIS_PORT = os.environ.get('REDIS_PORT')
    assert REDIS_HOST is not None
    assert REDIS_PORT is not None

    logger.debug('Redis connection info: %s:%s' % (REDIS_HOST, REDIS_PORT))

    # Ensure connection to redis is good
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    try:
        r.ping()
    except:
        logger.error('Could not connect to redis, exiting')
        exit()
    else:
        logger.debug('Connected to redis')

    # Iterate the queues, and check the length
    for queue_name, threshold in get_queues_and_thresholds(logger):
        logger.debug('Checking %s queue' % queue_name)

        q = Queue(queue_name, connection=r)
        queue_length = len(q)

        if queue_length >= threshold:
            logger.debug('%s queue is over threshold (length=%d, threshold=%d)' % (queue_name, queue_length, threshold))
            send_alert(logger, queue_name, queue_length)

    logger.debug('Queue checker finished')


if __name__ == "__main__":
    __main__()


def send_alert(logger, queue_name, queue_length):
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

    logger.debug('slack notification sent for %s' % queue_name)
