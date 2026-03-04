"""
Pydantic models for MLFlow run comparison.

Input: list of run_ids, primary metric name, optional secondary metric for tie-breaking.
Output: best run_id, optional artifact_uri, optional warnings (e.g. missing metrics).
"""
from typing import Optional

from pydantic import BaseModel, Field


# Metrics where higher is better (e.g. accuracy, F1, AUC, r2)
HIGHER_IS_BETTER = {"accuracy", "f1", "f1_score", "auc", "roc_auc", "r2", "r2_score", "precision", "recall"}


class CompareModelsRequest(BaseModel):
    """Request body for comparing models by run IDs."""

    run_ids: list[str] = Field(
        ...,
        min_length=1,
        description="List of MLFlow run IDs to compare (e.g. from mlflow.start_run().info.run_id).",
    )
    metric: str = Field(
        default="r2",
        description="Primary metric to compare (e.g. 'accuracy', 'f1', 'mse', 'r2'). Higher is better for accuracy/f1/auc/r2; lower is better for mse/mae.",
    )
    secondary_metric: Optional[str] = Field(
        default=None,
        description="Optional metric to break ties when primary metric values are equal.",
    )


class CompareModelsResponse(BaseModel):
    """Response with the best performing run and optional details."""

    best_run_id: str = Field(..., description="Run ID of the best performing model.")
    metric: str = Field(..., description="Metric used for comparison.")
    metric_value: float = Field(..., description="Value of the comparison metric for the best run.")
    artifact_uri: Optional[str] = Field(default=None, description="MLFlow artifact URI for the best run, for deployment.")
    warnings: list[str] = Field(default_factory=list, description="Warnings (e.g. runs excluded due to missing metric).")
