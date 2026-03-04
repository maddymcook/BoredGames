# Compare MLFlow Runs (Best Model by Metric)

This feature lets you compare two or more MLFlow runs by a performance metric and get back the **best run ID** (and optionally the artifact URI for deployment).

## Input: How to Provide Run IDs

- **Endpoint:** `POST /models/compare`
- **Content-Type:** `application/json`
- **Body:**
  - **`run_ids`** (required): List of MLFlow run IDs to compare. Each ID is the string returned by MLFlow when you log a run (e.g. `run.info.run_id` from `mlflow.start_run()` or from the MLFlow UI).
  - **`metric`** (optional, default `"r2"`): The primary metric used to compare runs. Must be a metric name that was logged for each run (e.g. `accuracy`, `f1`, `mse`, `r2`, `auc`).
  - **`secondary_metric`** (optional): If two runs have the same value for the primary metric, this metric is used to break the tie.

**Example:**

```json
{
  "run_ids": ["abc123", "def456", "ghi789"],
  "metric": "r2",
  "secondary_metric": "mse"
}
```

## How the Comparison Metric Is Defined

- **Higher is better** for: `accuracy`, `f1`, `f1_score`, `auc`, `roc_auc`, `r2`, `r2_score`, `precision`, `recall`. The run with the **largest** value wins.
- **Lower is better** for: `mse`, `mae`, and any other metric not in the list above. The run with the **smallest** value wins.
- **Ties:** If you provide `secondary_metric`, ties on the primary metric are broken by the secondary metric (same higher/lower rules).
- **Missing metric:** If a run does not have the chosen metric logged, that run is **excluded** from the comparison and a **warning** is added to the response. If no runs have the metric, the API returns an error.

## Output

- **200:** JSON with `best_run_id`, `metric`, `metric_value`, optional `artifact_uri`, and optional `warnings` (e.g. runs excluded due to missing metric).
- **400:** Invalid request (e.g. empty run_ids, validation errors) or all run IDs invalid / no run had the metric.
- **503:** MLFlow unreachable or other server error.

## Error Handling

- **Invalid run IDs:** If any run ID does not exist or is invalid, the API returns **400** with a message listing the invalid run ID(s).
- **No run IDs:** Returns **400** with a message that at least one run_id is required.
- **No comparable runs:** If every run is excluded (e.g. missing metric), returns **400** with a message explaining that no run could be compared.

## Example Flow

1. Engineer has two run IDs from MLFlow: `run_id_1`, `run_id_2`.
2. `POST /models/compare` with body `{"run_ids": ["run_id_1", "run_id_2"], "metric": "r2"}`.
3. Service fetches each run from MLFlow, reads metrics (e.g. `r2`, `mse`).
4. Compares by `r2` (higher is better), breaks ties with `mse` (lower is better) if `secondary_metric` is set.
5. Response: `{"best_run_id": "run_id_2", "metric": "r2", "metric_value": 0.85, "artifact_uri": "http://...", "warnings": []}`.

## Prerequisites

- MLFlow tracking server must be running. From the project root:
  - **All platforms:** `mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db`
  - **Windows (recommended):** Add `--workers 1` to avoid `WinError 10022` (socket error with multiple workers):
    ```powershell
    mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db --workers 1
    ```
- App config `TRACKING_URI` must point to that server (e.g. `http://localhost:8080`).
