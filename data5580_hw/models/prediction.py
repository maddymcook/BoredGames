from typing import Dict, Union, Optional, List, Any

from datetime import datetime
import pandas as pd

from pydantic import Field

from data5580_hw.models.base import LocalBaseModel, get_id

# Same order as sklearn.datasets.fetch_california_housing().feature_names — required
# for strict sklearn feature checks on DataFrame inputs.
CALIFORNIA_HOUSING_FEATURE_ORDER = (
    "MedInc",
    "HouseAge",
    "AveRooms",
    "AveBedrms",
    "Population",
    "AveOccup",
    "Latitude",
    "Longitude",
)


class Explanation(LocalBaseModel):
    name: str
    values: Dict

    id: str = Field(default_factory=get_id)


class Explanations(LocalBaseModel):
    explanations: List[Explanation] = Field(default_factory=list)


class Model(LocalBaseModel):
    name: str
    version: str
    type: str

    _model = None
    _explainer = None

    id: str = Field(default_factory=get_id)


class Prediction(LocalBaseModel):

    id: str = Field(default_factory=get_id)
    features: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(default_factory=dict)
    tags: Dict[str, Any] = Field(default_factory=dict)
    explanations: Optional[Explanations] = None
    label: Union[int, float, str, None] = None
    # Reduced-dimensional representation of the *input rows* (outer list) into
    # an embedding vector (inner list of floats).
    embeddings: Optional[List[List[float]]] = None
    # Optional per-request UMAP configuration.
    umap_params: Optional[Dict[str, Any]] = None
    actual: Union[int, float, str, None] = None
    threshold: Optional[float] = None

    model: Optional[Model] = None

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    def get_pandas_frame_of_inputs(self):
        if isinstance(self.features, list):
            # One row per datapoint.
            return pd.DataFrame(self.features)
        if self.model and self.model.name == "california-housing":
            f = self.features
            expected = set(CALIFORNIA_HOUSING_FEATURE_ORDER)
            if set(f.keys()) == expected:
                ordered = {k: f[k] for k in CALIFORNIA_HOUSING_FEATURE_ORDER}
                return pd.DataFrame(
                    [ordered], columns=list(CALIFORNIA_HOUSING_FEATURE_ORDER)
                )
        # One row for the provided feature vector.
        return pd.DataFrame([self.features], index=[0])
