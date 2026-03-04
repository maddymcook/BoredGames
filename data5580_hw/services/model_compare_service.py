"""
Service to compare MLFlow runs by a chosen metric and return the best run ID.

Uses the MLFlow gateway to fetch run metrics by run_id. Handles invalid run IDs,
missing metrics (excludes run with warning), and ties (secondary metric).
"""
from typing import Any

from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.models.compare import CompareModelsResponse, HIGHER_IS_BETTER


class ModelCompareService:
    """Compare MLFlow runs by performance metrics and return the best run."""

    @staticmethod
    def _metric_better(metric_name: str, value_a: float, value_b: float) -> bool:
        """True if value_a is better than value_b for the given metric."""
        higher = metric_name.lower() in HIGHER_IS_BETTER
        if higher:
            return value_a > value_b
        return value_a < value_b

    @staticmethod
    def compare_runs(
        run_ids: list[str],
        metric: str,
        secondary_metric: str | None = None,
    ) -> CompareModelsResponse:
        """
        Compare runs by the given metric; use secondary_metric to break ties.
        Invalid run IDs are reported as errors (raise). Runs missing the metric
        are excluded and a warning is added.
        """
        metric = metric.strip().lower()
        if secondary_metric:
            secondary_metric = secondary_metric.strip().lower()

        invalid_run_ids: list[str] = []
        runs_with_metrics: list[dict[str, Any]] = []
        warnings: list[str] = []

        for run_id in run_ids:
            try:
                run_data = mlflow_gateway.get_run_metrics(run_id)
            except Exception:
                invalid_run_ids.append(run_id)
                continue

            metrics = run_data.get("metrics", {})
            if metric not in metrics:
                warnings.append(f"Run {run_id} excluded: missing metric '{metric}'.")
                continue

            runs_with_metrics.append({
                "run_id": run_data["run_id"],
                "artifact_uri": run_data.get("artifact_uri"),
                "metrics": metrics,
            })

        if invalid_run_ids:
            raise ValueError(f"Invalid or not found run ID(s): {invalid_run_ids}.")

        if not runs_with_metrics:
            raise ValueError(
                "No run IDs could be compared. Provide valid run IDs and ensure "
                f"each run has metric '{metric}' logged in MLFlow."
            )

        # Sort so best is first: higher_is_better -> descending, else ascending.
        higher = metric in HIGHER_IS_BETTER
        sec_higher = secondary_metric and (secondary_metric in HIGHER_IS_BETTER)
        inf, ninf = float("inf"), float("-inf")

        def sort_key(r: dict) -> tuple:
            p = r["metrics"].get(metric, ninf if higher else inf)
            if not secondary_metric:
                return (-p,) if higher else (p,)
            s = r["metrics"].get(secondary_metric, ninf if sec_higher else inf)
            # Best first: for higher we want (-p, -s) so ascending sort gives max first
            if higher and sec_higher:
                return (-p, -s)
            if higher and not sec_higher:
                return (-p, s)
            if not higher and sec_higher:
                return (p, -s)
            return (p, s)

        runs_with_metrics.sort(key=sort_key)
        best = runs_with_metrics[0]
        return CompareModelsResponse(
            best_run_id=best["run_id"],
            metric=metric,
            metric_value=best["metrics"][metric],
            artifact_uri=best.get("artifact_uri"),
            warnings=warnings,
        )


model_compare_service = ModelCompareService()
