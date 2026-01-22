from flask import blueprints

metrics = blueprints.Blueprint("metrics", __name__)

@metrics.route("/metrics", methods=["GET"])
def get_metrics():
    return generate_latest(registry), 200, { "Content-Type": 'text/plain';version=0.0.4; charset=utf-8')
    }