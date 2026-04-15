from typing import List
import json
from datetime import datetime

from sqlalchemy import CLOB, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped

from data5580_hw.services.database.database_client import db
from data5580_hw.models.prediction import Prediction, Model, Explanations, Explanation


class ExplanationSql(db.Model):
    __tablename__ = "explanations"

    id: Mapped[str] = mapped_column(db.String(120), primary_key=True)
    name: Mapped[str] = mapped_column(db.String(120), nullable=False)
    values: Mapped[str] = mapped_column(CLOB, nullable=False)
    updated: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    created: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    prediction_id: Mapped[str] = mapped_column(
        db.String(120), ForeignKey("predictions.id"), nullable=False
    )

    @classmethod
    def from_prediction(cls, prediction: Prediction) -> List["ExplanationSql"]:
        out: list[ExplanationSql] = []
        if not prediction.explanations:
            return out
        for item in prediction.explanations.explanations:
            out.append(
                cls(
                    id=item.id,
                    name=item.name,
                    values=json.dumps(item.values),
                    prediction_id=prediction.id,
                )
            )
        return out
    def from_prediction(cls, prediction: Prediction) -> List['ExplanationSql']:
        return [
            cls(
                id=prediction.explanations.explanations[idx].id,
                name=prediction.explanations.explanations[idx].name,
                values=json.dumps(prediction.explanations.explanations[idx].values),
                prediction_id=prediction.id,
            )
            for idx in range(len(prediction.explanations.explanations))
        ]


class ModelSql(db.Model):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(db.String(120), primary_key=True)
    model_type: Mapped[str] = mapped_column(db.String(120), nullable=False)
    model_name: Mapped[str] = mapped_column(db.String(4000), nullable=False)
    model_version: Mapped[str] = mapped_column(db.String(4000), nullable=False)
    updated: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    created: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    predictions: Mapped[List["PredictionSQL"]] = relationship(
        "PredictionSQL", back_populates="model"
    )

    @classmethod
    def from_model(cls, model: Model) -> "ModelSql":
    def from_model(cls, model: Model) -> 'ModelSql':
        model_ = db.session.query(ModelSql).filter(
            (ModelSql.model_name == model.name),
            (ModelSql.model_version == model.version),
        ).first()

        if not model_:
            model_ = cls(
                id=model.id,
                model_type=model.type,
                model_name=model.name,
                model_version=model.version,
            )
            db.session.add(model_)
            db.session.flush()
        return model_

    def __repr__(self):
        return f"Model Name {self.model_name}, Model Version {self.model_version}"


class PredictionSQL(db.Model):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(db.String(120), primary_key=True)
    features: Mapped[str] = mapped_column(CLOB, nullable=False)
    tags: Mapped[str] = mapped_column(CLOB)
    label: Mapped[str] = mapped_column(db.String(120), nullable=False)
    embeddings: Mapped[str] = mapped_column(CLOB, nullable=True)
    actual: Mapped[str] = mapped_column(db.String(120), nullable=True)
    threshold: Mapped[float] = mapped_column(db.Float, nullable=True)
    created: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    updated: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    model_id: Mapped[str] = mapped_column(
        db.String(120), ForeignKey("models.id"), nullable=False
    )
    model: Mapped["ModelSql"] = relationship("ModelSql", back_populates="predictions")
    explanations: Mapped[List["ExplanationSql"]] = relationship(
        "ExplanationSql", uselist=True
    )

    @classmethod
    def from_prediction(cls, prediction: Prediction, model: ModelSql) -> "PredictionSQL":
        return cls(
            id=prediction.id,
            features=json.dumps(prediction.features),
            tags=json.dumps(prediction.tags),
            label=str(prediction.label),
            embeddings=json.dumps(prediction.embeddings) if prediction.embeddings is not None else None,
            actual=str(prediction.actual) if prediction.actual is not None else None,
            label=prediction.label,
            embeddings=(
                json.dumps(prediction.embeddings)
                if prediction.embeddings is not None
                else None
            ),
            actual=prediction.actual,
            threshold=prediction.threshold,
            created=prediction.created,
            updated=prediction.updated,
            model_id=model.id,
        )

    def to_prediction(self) -> Prediction:
        prediction_ = Prediction(
            id=self.id,
            features=json.loads(self.features) if self.features else {},
            tags=json.loads(self.tags) if self.tags else {},
            label=self.label,
            embeddings=json.loads(self.embeddings) if self.embeddings else None,
            embeddings=(
                json.loads(self.embeddings) if self.embeddings is not None else None
            ),
            actual=self.actual,
            threshold=self.threshold,
            created=self.created,
            updated=self.updated,
            model=Model(
                id=self.model_id,
                name=self.model.model_name,
                version=self.model.model_version,
                type=self.model.model_type,
            ),
        )

        if self.explanations:
            explanations_ = Explanations()
            for explanation_sql in self.explanations:
                explanations_.explanations.append(
                    Explanation(
                        id=explanation_sql.id,
                        name=explanation_sql.name,
                        values=json.loads(explanation_sql.values),
                    )
                )

            if isinstance(self.explanations, ExplanationSql):
                explanation_sql = [self.explanations]
            else:
                explanation_sql = self.explanations

            for explanation in explanation_sql:
                explanations_.explanations.append(
                    Explanation(
                        id=explanation.id,
                        name=explanation.name,
                        values=json.loads(explanation.values),
                    )
                )

            prediction_.explanations = explanations_

        return prediction_

    def __repr__(self) -> str:
        return f"<Prediction {self.id}>"
