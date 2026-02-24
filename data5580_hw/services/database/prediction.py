from typing import List
import json
from datetime import datetime

from sqlalchemy import CLOB, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped

from data5580_hw.services.database.database_client import db
from data5580_hw.models.prediction import Prediction, Model


class ModelSql(db.Model):
    __tablename__ = 'models'

    id: Mapped[str] = mapped_column(db.String(120), primary_key=True)

    model_type: Mapped[str] = mapped_column(db.String(120), nullable=False)
    model_name: Mapped[str] = mapped_column(db.String(4000), nullable=False)
    model_version: Mapped[str] = mapped_column(db.String(4000), nullable=False)

    updated: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    created: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)

    predictions: Mapped[List['PredictionSQL']] = relationship("PredictionSQL", back_populates="model")

    @classmethod
    def from_model(cls, model: Model) -> 'ModelSql':

        model_ = db.session.query(ModelSql).filter(
            (ModelSql.model_name == model.name)
            , (ModelSql.model_version == model.version)
        ).first()

        if not model_:
            model_ = cls(
                id=model.id
                , model_type=model.type
                , model_name=model.name
                , model_version=model.version
            )

            db.session.add(model_)

        return model_

    def __repr__(self):
        return f'Model Name {self.model_name}, Model Version {self.model_version}'


class PredictionSQL(db.Model):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(db.String(120), primary_key=True)

    features: Mapped[dict] = mapped_column(CLOB, nullable=False)
    tags: Mapped[dict] = mapped_column(CLOB)
    label: Mapped[str] = mapped_column(db.String(120), nullable=False)
    actual: Mapped[str] = mapped_column(db.String(120), nullable=True)
    threshold: Mapped[float] = mapped_column(db.Float, nullable=True)

    created: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    updated: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)

    model_id: Mapped[str] = mapped_column(db.String(120), ForeignKey('models.id'), nullable=False)
    model: Mapped['ModelSql'] = relationship("ModelSql", back_populates="predictions")

    @classmethod
    def from_prediction(cls, prediction: Prediction, model: Model) -> 'PredictionSQL':
        return cls(
            id=prediction.id,
            features=json.dumps(prediction.features),
            tags=json.dumps(prediction.tags),
            label=prediction.label,
            actual=prediction.actual,
            threshold=prediction.threshold,
            created=prediction.created,
            updated=prediction.updated,
            model_id=model.id,
        )

    def to_prediction(self) -> Prediction:
        return Prediction(
            id=self.id,
            features=json.loads(self.features),
            tags=json.loads(self.tags),
            label=self.label,
            actual=self.actual,
            threshold=self.threshold,
            created=self.created,
            updated=self.updated,
            model=Model(
                id=self.model_id,
                name=self.model.model_name,
                version=self.model.model_version,
                type=self.model.model_type,
            )
        )

    def __repr__(self) -> str:
        return f"<Prediction {self.id}>"
