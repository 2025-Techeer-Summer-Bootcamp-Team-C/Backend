from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
import logging
from kombu import Queue

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

app = Celery('backend', broker='amqp://guest:guest@rabbitmq:5672/')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.task_routes = {
    # I/O 작업
    "fitting.tasks.run_vto_edit_url_task": {"queue": "io"},
    "fitting.tasks.edit_bg_task":          {"queue": "io"},
    "fitting.tasks.save_to_s3_and_db":     {"queue": "io"},
    # CPU 작업
    "fitting.tasks.resize":                {"queue": "cpu"},
}

app.conf.task_queues = (
    Queue("io"),   # I/O 전용
    Queue("cpu"),  # CPU 전용
)

app.autodiscover_tasks()

app.log.setup_logging_subsystem()
logger = logging.getLogger('backend')
logger.setLevel(logging.DEBUG)