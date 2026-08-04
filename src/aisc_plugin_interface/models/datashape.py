from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


SemanticType = Literal["numeric", "categorical", "datetime", "text", "boolean"]
FeatureRole = Literal["feature", "target", "date", "ignore"]


class Feature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    dtype: str = Field(min_length=1)
    semantic_type: SemanticType
    role: FeatureRole = "feature"
    null_count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    min: float | int | None = None
    max: float | int | None = None
    mean: float | None = None
    std: float | None = None
    categories: list[Any] | None = None
    category_mapping: dict[str, str] | None = None

    @model_validator(mode="after")
    def validate_category_fields(self):
        if self.category_mapping is not None and self.semantic_type != "categorical":
            raise ValueError("category_mapping is only valid for categorical features")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("feature min must not exceed max")
        return self


class DataShape(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    source_dataset_pid: UUID
    source_format: Literal["csv", "parquet"]
    derived_at: datetime
    row_count: int = Field(ge=0)
    features: list[Feature] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_feature_names(self):
        names = [feature.name for feature in self.features]
        if len(names) != len(set(names)):
            raise ValueError("datashape feature names must be unique")
        return self
