"""Coverage for prometheus hooks when not in TESTING mode."""

from flask import Flask

from data5580_hw.monitoring import after_request, before_request, init_metrics


def test_before_and_after_request_record_metrics():
    app = Flask(__name__)
    with app.test_request_context("/hello"):
        before_request()
        resp = app.response_class("ok", 200)
        out = after_request(resp)
        assert out is resp


def test_init_metrics_registers_hooks_when_not_testing():
    app = Flask(__name__)
    app.config["TESTING"] = False
    init_metrics(app)
    assert before_request in app.before_request_funcs[None]
    assert after_request in app.after_request_funcs[None]
