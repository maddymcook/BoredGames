# app.py
from flask import Flask, request, jsonify
from celery import Celery
import time
import os

# Flask app setup
app = Flask(__name__)

# Celery configuration
app.config['broker_url'] = os.getenv('broker_url', 'redis://localhost:6379/0')
app.config['result_backend'] = os.getenv('result_backend', 'redis://localhost:6379/0')

# Create Celery instance
celery = Celery(app.name, broker=app.config['broker_url'])
celery.conf.update(app.config)

# Background task
@celery.task(bind=True)
def long_task(self, duration):
    """Simulates a long-running task."""
    for i in range(duration):
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'current': i + 1, 'total': duration})
    return {'status': 'Task completed!', 'total_seconds': duration}

@app.route('/start-task', methods=['POST'])
def start_task():
    """Start a background task."""
    try:
        print(request.data)
        duration = 5 #int(request.json.get('duration', 5))
        if duration <= 0:
            return jsonify({'error': 'Duration must be positive'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid duration'}), 400

    task = long_task.apply_async(args=[duration])
    return jsonify({'task_id': task.id}), 202

@app.route('/task-status/<task_id>', methods=['GET'])
def task_status(task_id):
    """Check task status."""
    task = long_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        return jsonify({'state': task.state, 'status': 'Pending...'})
    elif task.state == 'PROGRESS':
        return jsonify({'state': task.state, 'progress': task.info})
    elif task.state == 'SUCCESS':
        return jsonify({'state': task.state, 'result': task.info})
    else:
        # FAILURE or RETRY
        return jsonify({'state': task.state, 'error': str(task.info)}), 500

if __name__ == '__main__':
    app.run(debug=True)


# launch WSL
# Launch Redis
# python app.py
# celery -A app.celery worker --loglevel=info -P gevent
# curl.exe -X POST http://localhost:5000/start-task -H "Content-Type: application/json" -d '{"duration": "10"}'
# celery --broker=redis://localhost:6379/0 flower --address='localhost


import os
import tempfile

from flask.cli import load_dotenv

os.environ['PROMETHEUS_MULTIPROC_DIR'] = tempfile.mkdtemp()

# Standardlibrary
import  logging

# Installed
from flask import Flask, jsonify

# Local
from data5580_hw.routes import init_blueprints
from data5580_hw.services.database.database_client import init_db
from data5580_hw.monitoring import init_metrics
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway

logging.basicConfig(level=logging.DEBUG)
# Avoid urllib3 DEBUG on stderr so PowerShell does not treat it as an error
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

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

    from data5580_hw.gateways.arize_gateway import arize_gateway
    arize_gateway.init_app(app)

    return app


if __name__ == "__main__":
    print("Starting the application...")
    app = create_app()
    app.run(debug=True)
