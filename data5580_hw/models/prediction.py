from typing import Dict, Union, Optional, List, Any

from datetime import datetime
import pandas as pd

from pydantic import Field

from data5580_hw.models.base import LocalBaseModel, get_id


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
        # One row for the provided feature vector.
        return pd.DataFrame([self.features], index=[0])

    def get_pandas_frame_aligned_to_model(self, raw_model: Any) -> pd.DataFrame:
        """
        Column order matches sklearn feature_names_in_ when present (JSON may reorder keys).

        Whole numbers from JSON become int64 in pandas; MLflow pyfunc models that declare
        double columns reject int64. Coerce numeric dtypes to float64 before inference.
        """
        df = self.get_pandas_frame_of_inputs()
        names = getattr(raw_model, "feature_names_in_", None)
        if names is not None and not df.empty:
            missing = set(names) - set(df.columns)
            if missing:
                raise ValueError(f"Missing features: {sorted(missing)}")
            df = df[list(names)]
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].astype("float64")
        return df
