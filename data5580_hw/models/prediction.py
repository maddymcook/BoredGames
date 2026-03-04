from typing import Dict, Union, Optional, List

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
    features: Dict = Field(default_factory=dict)
    tags: Dict = Field(default_factory=dict)
    explanations: Optional[Explanations] = None
    label: Union[int, float, str, None] = None
    actual: Union[int, float, str, None] = None
    threshold: Optional[float] = None

    model: Optional[Model] = None

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    def get_pandas_frame_of_inputs(self):

        return pd.DataFrame([self.features], index=[0])
