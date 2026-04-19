import os
import tempfile
import logging

from flask import Flask, jsonify
from flask.cli import load_dotenv

from data5580_hw.routes import init_blueprints
from data5580_hw.services.database.database_client import init_db
from data5580_hw.gateways.arize_gateway import arize_gateway
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.gateways.llm_gateway import llm_gateway

if not os.path.isdir(os.environ.get("PROMETHEUS_MULTIPROC_DIR", "")):
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = tempfile.mkdtemp()

# INFO keeps local runs readable; set LOG_LEVEL=DEBUG when troubleshooting.
_log_level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
if not isinstance(_log_level, int):
    _log_level = logging.INFO
logging.basicConfig(level=_log_level)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

# Before Numba/UMAP import: reduce compiler debug noise (optional override via env)
os.environ.setdefault("NUMBA_DEBUG", "0")

from flask.cli import load_dotenv

os.environ['PROMETHEUS_MULTIPROC_DIR'] = tempfile.mkdtemp()

# Standardlibrary
import logging
from pathlib import Path

# Installed
from flask import Flask, jsonify

# Local
from data5580_hw.routes import init_blueprints
from data5580_hw.services.database.database_client import init_db
from data5580_hw.monitoring import init_metrics
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.gateways.arize_gateway import arize_gateway
from data5580_hw.celery_app import init_celery

logging.basicConfig(level=logging.DEBUG)
# Avoid urllib3 DEBUG on stderr so PowerShell does not treat it as an error
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
# Suppress Numba JIT-compiler internal DEBUG spam (UMAP / scipy.sparse paths)
logging.getLogger("numba").setLevel(logging.WARNING)
logging.getLogger("llvmlite").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    # Package .env first (reliable when cwd is repo root); optional cwd .env overrides.
    load_dotenv(Path(__file__).resolve().parent / ".env")
    load_dotenv()

    from data5580_hw.config import Config

    config = Config()

    app.config.from_object(config)

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
    arize_gateway.init_app(app)
    init_celery(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
