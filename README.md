DATA 5580 | Machine Learning Operations | Homework Application
==============================

This repository contains a small Flask web application used for DATA 5580 homework assignments. It demonstrates how to build and test a web API around machine‑learning models, with a focus on reproducibility, observability, and interpretability.

What’s in this repo (and why you might care)
--------------------------------------------

- **Flask API with typed models**: Endpoints for managing users and running model predictions, using Pydantic models for input/output validation.
- **ML model serving via MLflow**: A gateway layer that can load models and explainers from an MLflow tracking server.
- **SHAP explanations for predictions (HW6)**: After each prediction, the API can compute and return feature‑level SHAP values, and persist them for later inspection.
- **SQLAlchemy persistence**: Users, predictions, and SHAP explanations are stored in a relational database (SQLite by default).
- **Monitoring & metrics**: Basic Prometheus metrics for request count and latency.
- **Comprehensive tests with coverage**: `pytest` test suite that hits the main user and prediction flows, including error handling and SHAP behavior (current coverage ≥ 80%).

If you’re interested in:

- How to wrap an ML model in a production‑style API,
- How to integrate SHAP/MLflow into a Flask app, or
- How to structure and test a small but realistic service,

then this repo is relevant. If you’re looking for a large, production‑ready system or a general‑purpose ML library, this is probably too small and assignment‑focused.

High‑level structure
--------------------

- `data5580_hw/app.py` – Flask app factory (`create_app`) and wiring for DB, blueprints, metrics, and MLflow gateway.
- `data5580_hw/routes/` – Blueprint routes for users, predictions, metrics, and model comparison.
- `data5580_hw/controllers/` – Request/response logic and error handling.
- `data5580_hw/models/` – Pydantic models for users, predictions, and model metadata.
- `data5580_hw/services/` – Business logic:
  - `model_service.py` – Runs model inference.
  - `explainer_service.py` – Computes SHAP explanations.
  - `model_compare_service.py` – Compares MLflow runs by a metric.
- `data5580_hw/services/database/` – SQLAlchemy models and DB init helpers.
- `data5580_hw/gateways/mlflow_gateway.py` – Integration with MLflow tracking server and model registry.
- `tests/test_app.py` – End‑to‑end style tests for the main routes.

Running the app locally
-----------------------

1. **Install dependencies** (from the repo root):

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Flask app**:

   ```bash
   export FLASK_APP=data5580_hw.app:create_app
   flask run
   ```

   By default the app uses SQLite (`instance/data.db`) and expects an MLflow tracking URI from `data5580_hw/config.py`. For homework/testing, the MLflow‑dependent parts are mocked or skipped when `TESTING=1`.

Running tests and coverage
--------------------------

From the `data5580_hw` directory:

```bash
pytest tests/test_app.py -v --cov=data5580_hw --cov-report=term-missing --cov-branch
```

This runs the full test suite and prints a line‑by‑line coverage summary. The HW6 work specifically adds tests around the prediction and SHAP logic, as well as a lookup endpoint (`GET /predictions/<prediction_id>`) so that prediction records (and their SHAP values) can be retrieved and inspected.
