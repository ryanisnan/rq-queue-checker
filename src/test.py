from rq import Queue
from run import dummy_job
from run import get_queue_config
from run import get_redis_connection
from run import process_queue
import json
import logging
import os
import redis
import sys
import unittest


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.ERROR)

logger.addHandler(handler)


class GetRedisConnectionTestCase(unittest.TestCase):
    def test_good_connection(self):
        get_redis_connection(os.environ.get('REDIS_HOST', 'localhost'), os.environ.get('REDIS_PORT', '6379'))

    def test_bad_connection(self):
        with self.assertRaises(redis.exceptions.ConnectionError):
            get_redis_connection('fake-server', '8181')


class GetQueueConfigTestCase(unittest.TestCase):
    def test_bad_config(self):
        with self.assertRaises(ValueError):
            bad_json = 'my dog is kingston'
            get_queue_config(bad_json)

    def test_good_config(self):
        good_json = {
            'high': 100,
            'medium': 200,
            'low': 500
        }
        queue_config = get_queue_config(json.dumps(good_json))
        assert len(queue_config.items()) == 3
        assert queue_config['medium'] == 200


class TestProcessQueueTestCase(unittest.TestCase):
    def setUp(self):
        # Set up a connection and queues to work with
        self.r = get_redis_connection(os.environ.get('REDIS_HOST', 'localhost'), os.environ.get('REDIS_PORT', '6379'))
        self.high_queue = Queue('high', connection=self.r)

        # Add 100 items to the high queue
        for i in range(100):
            self.high_queue.enqueue(dummy_job)

    def tearDown(self):
        self.high_queue.delete(delete_jobs=True)

    def test_process_queue_over_threshold(self):
        queue_name = 'high'
        threshold = 50

        os.environ['QUEUE_CONFIG'] = '{"%s":%d}' % (queue_name, threshold)

        assert process_queue(queue_name, threshold) is True

    def test_process_queue_under_threshold(self):
        queue_name = 'high'
        threshold = 150

        os.environ['QUEUE_CONFIG'] = '{"%s":%d}' % (queue_name, threshold)

        assert process_queue(queue_name, threshold) is False


if __name__ == "__main__":
    unittest.main()
