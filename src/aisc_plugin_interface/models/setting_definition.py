import enum

from pydantic import BaseModel, ConfigDict, field_validator


class SettingCategory(str, enum.Enum):
    SECRETS = "secrets"
    DATASHAPE = "datashape"
    GENERAL = "general"


class SettingValueType(str, enum.Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


class SettingDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    category: SettingCategory
    value_type: SettingValueType | None = None
    required: bool = True

    @field_validator("key")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not value or not value.replace("_", "").isalnum() or not value[0].isalpha():
            raise ValueError("setting key must start with a letter and contain only letters, numbers, and underscores")
        return value
