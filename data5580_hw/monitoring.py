import time

from flask import request
from prometheus_client import CollectorRegistry, Counter, Histogram, multiprocess

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry=registry)

REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'http_status'],
                        registry=registry)
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds',
                            ['method', 'endpoint', 'http_status'], registry=registry)


def before_request():
    request.start_time = time.time()


def after_request(response):
    start = getattr(request, "start_time", None)
    latency = (time.time() - start) if start is not None else 0.0
    path = request.url_rule.rule if request.url_rule is not None else request.path
    status = str(response.status_code)
    REQUEST_COUNT.labels(method=request.method, endpoint=path, http_status=status).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=path, http_status=status).observe(latency)
    return response


def init_metrics(app):

    if not app.config["TESTING"]:
        with app.app_context():
            app.before_request(before_request)

            app.after_request(after_request)