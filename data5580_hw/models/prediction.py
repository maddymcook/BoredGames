from typing import Dict, Union, Optional

from datetime import datetime

from pydantic import Field

from data5580_hw.models.base import LocalBaseModel, get_id


class Model(LocalBaseModel):
    name: str
    version: str
    type: str

    _model = None
    id: str = Field(default_factory=get_id)


class Prediction(LocalBaseModel):

    id: str = Field(default_factory=get_id)
    features: Dict = Field(default_factory=dict)
    tags: Dict = Field(default_factory=dict)
    label: Union[int, float, str, None] = None
    actual: Union[int, float, str, None] = None
    threshold: Optional[float] = None

    model: Optional[Model] = None

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)


