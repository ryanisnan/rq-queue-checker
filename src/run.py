from rq import Queue
import json
import logging
import os
import redis
import requests
import sys
import uuid
import boto3
import datetime


class LoggingTransactionAdapter(logging.LoggerAdapter):
    """
    Add a transaction ID to each log message corresponding this adapter.
    Used for instrumenting a request (aka transaction)'s log messages with
    a unique UUID for monitoring purposes.
    """
    def __init__(self, *args, **kwargs):
        self.refresh_trn_id()
        kwargs['extra'] = {}
        super().__init__(*args, **kwargs)

    def process(self, msg, kwargs):
        return '[trn: %s] %s' % (getattr(self, 'trn_id'), msg), kwargs

    def refresh_trn_id(self, *args, **kwargs):
        setattr(self, 'trn_id', str(uuid.uuid4()))


base_logger = logging.getLogger(__name__)
base_logger.setLevel(int(os.environ.get('LOGLEVEL', logging.DEBUG)))

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(int(os.environ.get('LOGLEVEL', logging.DEBUG)))

base_logger.addHandler(handler)
logger = LoggingTransactionAdapter(base_logger)


def get_redis_connection(redis_host, redis_port):
    """
    Build and return a redis connection based on the passed-in host and port.
    Verifies that the connection is valid or aborts the script.
    """
    logger.debug('Redis connection info: %s:%s' % (redis_host, redis_port))

    r = redis.Redis(host=redis_host, port=redis_port, db=1)

    # Ensure connection to redis is good
    r.ping()
    logger.debug('Connected to redis')

    return r


def get_queue_config(serialized_json):
    """
    Returns a python dict containing queue configuration.
    """
    logger.debug('Queue configuration: %s' % serialized_json)

    try:
        queue_config = json.loads(serialized_json)
    except:
        raise ValueError('Could not parse queue configuration as JSON')

    return queue_config


def process_queue(queue_name, threshold):
    """
    Given a queue name and a threshold figure, will attempt to check if
    the length of the queue is above the threshold. If so, it will attempt to
    send an alert.

    Returns True if an alert was triggered, and False if not.
    """
    r = get_redis_connection(os.environ.get('REDIS_HOST', 'localhost'), os.environ.get('REDIS_PORT', '6379'))

    queue = Queue(queue_name, connection=r)
    length = len(queue)
    send_alert(queue_name, length, 'cloudwatch')
    logger.debug('Queue %s has a length of %d' % (queue_name, length))

    if length >= threshold:
        logger.debug('Triggering an alert for %s' % queue_name)
        send_alert(queue_name, length, 'slack')
        return True

    return False

def dummy_job():
    """
    Dummy job for use in the test suite.
    """
    pass

def send_alert(queue_name, queue_length, alert_type):
    """
    Send an alert via slack to a specific webhook address notifying users of the
    queue length.
    Returns True if an alert was sent.
    """
    if alert_type == 'slack':
        SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

        if not SLACK_WEBHOOK_URL:
            logger.warning('SLACK_WEBHOOK_URL was not found in the environment, no alert will be sent.')
            return False

        payload = {'text': ':fire::fire::fire: *%s queue length alert - %d* :fire::fire::fire:' % (queue_name, queue_length)}
        requests.post(SLACK_WEBHOOK_URL, json=payload)

        logger.debug('Slack notification sent for %s' % queue_name)
        return True
    elif alert_type == 'cloudwatch':
        cloudwatch_client = boto3.client('cloudwatch')
        cloudwatch_client.put_metric_data(
            Namespace="RQMetrics-%s" % os.environ.get("ENVIRONMENT", "None"),
            MetricData=[
                {
                    'MetricName': queue_name,
                    "Dimensions": [
                        {
                            "Name": "queue_name",
                            "Value": queue_name
                        },
                    ],
                    "Value": float(queue_length),
                    'Timestamp': datetime.datetime.now(),
                    'Unit': 'None'
                }
            ]
        )
        return True
    else:
        return False


def __main__():
    logger.refresh_trn_id()
    logger.debug('Running queue checker')

    queue_config = get_queue_config(os.environ.get('QUEUE_CONFIG', '{}'))
    for queue_name, threshold in queue_config.items():
        process_queue(queue_name, threshold)

    logger.debug('Queue checker finished')


if __name__ == "__main__":
    __main__()
