import os
import tempfile
import logging

from flask import Flask, jsonify
from flask.cli import load_dotenv

from data5580_hw.routes import init_blueprints
from data5580_hw.services.database.database_client import init_db
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.gateways.llm_gateway import llm_gateway

if not os.path.isdir(os.environ.get("PROMETHEUS_MULTIPROC_DIR", "")):
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = tempfile.mkdtemp()

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    load_dotenv()
    from data5580_hw.monitoring import init_metrics

    from data5580_hw.config import Config

    app.config.from_object(Config())
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    init_db(app)

    @app.route("/", methods=["GET"])
    def home():
        return jsonify({"message": "Hello, Flask!"})

    init_blueprints(app)
    init_metrics(app)
    mlflow_gateway.init_app(app)
    llm_gateway.init_app(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
