# Overview

`rq-queue-checker` is a simple container that checks queues in the [Python RQ](https://python-rq.org/) async queue system, and posts alerts to Slack.

It is designed to run only once, and is thus best meant to be ran on a cron, or in a lambda perhaps.

This project is available on docker hub at [ryanisnan/rq-queue-checker](https://cloud.docker.com/repository/docker/ryanisnan/rq-queue-checker)

# Running the Tests

```
git clone git@github.com:ryanisnan/rq-queue-checker
cd rq-queue-checker
docker-compose -f docker-compose.test.yml up --build --exit-code-from queue_checker
```

# Running Locally

The container respects the following configuration variables:

- `REDIS_HOST` - Hostname of the redis server
- `REDIS_PORT` - Port of the redis server
- `QUEUE_CONFIG` - Stringified JSON object with queue/threshold key/value pairs, e.g. `{"high":1000,"default":2000}`
- `SLACK_WEBHOOK_URL` - Webhook for making slack channel posts
- `LOGLEVEL` - The level of logging output you would like. Default=10 (Debug), corresponds to [python's log levels](https://docs.python.org/3/library/logging.html#logging-levels).

# Contributing

Ensure that your contribution has tests, and submit a PR.
